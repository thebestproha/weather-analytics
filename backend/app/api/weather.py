from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.deps import get_db
from backend.app.models.weather import Weather
from backend.app.services.ml_predictor import (
    predict_next_hour,
    predict_next_24_hours,
    predict_next_7_days
)

router = APIRouter(tags=["weather"])

# ---------- CURRENT ----------
@router.get("/current/{city}")
def current(city: str, db: Session = Depends(get_db)):
    row = (
        db.query(Weather)
        .filter(Weather.city == city)
        .order_by(Weather.recorded_at.desc())
        .first()
    )
    if not row:
        return {"city": city, "temperature": None}

    return {
        "city": city,
        "temperature": round(float(row.temperature), 2),
        "recorded_at": row.recorded_at.isoformat()
    }

# ---------- HISTORY ----------
@router.get("/hourly/{city}")
def hourly(city: str, db: Session = Depends(get_db)):
    rows = (
        db.query(Weather)
        .filter(Weather.city == city)
        .order_by(Weather.recorded_at)
        .all()
    )
    return [{"temperature": r.temperature, "recorded_at": r.recorded_at} for r in rows]

@router.get("/daily/{city}")
def daily(city: str, db: Session = Depends(get_db)):
    rows = db.query(
        func.date(Weather.recorded_at),
        func.avg(Weather.temperature)
    ).filter(
        Weather.city == city
    ).group_by(
        func.date(Weather.recorded_at)
    ).all()

    return [{"day": d, "avg_temp": round(t,2)} for d,t in rows]

# ---------- PREDICTIONS ----------
@router.get("/predict/1h/{city}")
def predict_1h(city: str):
    y = predict_next_hour(city)
    return {"city": city, "temp": y}

@router.get("/predict/24h/{city}")
def predict_24h(city: str):
    return {
        "city": city,
        "temps": predict_next_24_hours(city)
    }

@router.get("/predict/7d/{city}")
def predict_7d(city: str):
    return {
        "city": city,
        "temps": predict_next_7_days(city)
    }
