from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.deps import get_db
from backend.app.models.weather import Weather
from backend.app.services.weather_fetcher import fetch_and_store
from backend.app.services.ml import train_and_predict

router = APIRouter(prefix="/weather", tags=["weather"])

@router.get("/current/{city}")
def current(city: str, db: Session = Depends(get_db)):
    w = db.query(Weather)\
        .filter(Weather.city.ilike(city))\
        .order_by(Weather.recorded_at.desc())\
        .first()

    if not w:
        return {"error": "no data available"}

    return {
        "city": w.city,
        "temperature": w.temperature,
        "humidity": w.humidity,
        "pressure": w.pressure,
        "wind_speed": w.wind_speed,
        "recorded_at": w.recorded_at
    }


@router.get("/hourly/{city}")
def hourly(city: str, db: Session = Depends(get_db)):
    rows = db.query(Weather).filter(
        Weather.city.ilike(city)
    ).order_by(Weather.recorded_at).all()

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
def predict(city: str):
    return train_and_predict(city)
