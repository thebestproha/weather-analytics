from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.deps import get_db
from backend.app.models.weather import Weather
from backend.app.services.ml import predict_next_hour

router = APIRouter(prefix="/weather", tags=["weather"])

@router.get("/current/{city}")
def current(city: str, db: Session = Depends(get_db)):
    # 1️⃣ Try LIVE API data first
    live = db.query(Weather)\
        .filter(
            Weather.city.ilike(city),
            Weather.source == "API"
        )\
        .order_by(Weather.recorded_at.desc())\
        .first()

    if live:
        return {
            "city": live.city,
            "temperature": live.temperature,
            "humidity": live.humidity,
            "pressure": live.pressure,
            "wind_speed": live.wind_speed,
            "source": "API",
            "recorded_at": live.recorded_at
        }

    # 2️⃣ Fallback to ERA5 (most recent)
    hist = db.query(Weather)\
        .filter(
            Weather.city.ilike(city),
            Weather.source == "ERA5"
        )\
        .order_by(Weather.recorded_at.desc())\
        .first()

    if hist:
        return {
            "city": hist.city,
            "temperature": hist.temperature,
            "humidity": hist.humidity,
            "pressure": hist.pressure,
            "wind_speed": hist.wind_speed,
            "source": "ERA5 (fallback)",
            "recorded_at": hist.recorded_at
        }

    return {"error": "no data available"}


@router.get("/hourly/{city}")
def hourly(city: str, db: Session = Depends(get_db)):
    rows = db.query(Weather)\
        .filter(Weather.city.ilike(city))\
        .order_by(Weather.recorded_at)\
        .all()

    return [
        {
            "temperature": r.temperature,
            "recorded_at": r.recorded_at
        }
        for r in rows
    ]


@router.get("/daily/{city}")
def daily(city: str, db: Session = Depends(get_db)):
    rows = db.query(
        func.date(Weather.recorded_at).label("day"),
        func.avg(Weather.temperature).label("avg_temp")
    ).filter(
        Weather.city.ilike(city)
    ).group_by("day").order_by("day").all()

    return [
        {"day": day, "avg_temp": round(temp, 2)}
        for day, temp in rows
    ]


@router.get("/monthly/{city}")
def monthly(city: str, db: Session = Depends(get_db)):
    rows = db.query(
        func.strftime("%Y-%m", Weather.recorded_at).label("month"),
        func.avg(Weather.temperature).label("avg_temp")
    ).filter(
        Weather.city.ilike(city)
    ).group_by("month").order_by("month").all()

    return [
        {"month": month, "avg_temp": round(temp, 2)}
        for month, temp in rows
    ]


@router.get("/yearly/{city}")
def yearly(city: str, db: Session = Depends(get_db)):
    rows = db.query(
        func.strftime("%Y", Weather.recorded_at).label("year"),
        func.avg(Weather.temperature).label("avg_temp")
    ).filter(
        Weather.city.ilike(city)
    ).group_by("year").order_by("year").all()

    return [
        {"year": year, "avg_temp": round(temp, 2)}
        for year, temp in rows
    ]


@router.get("/predict/{city}")
def predict(city: str, db: Session = Depends(get_db)):
    p = predict_next_hour(db, city)
    return {
        "city": city,
        "next_hour_temp": p
    }

