from datetime import datetime
from statistics import mean
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.weather import Weather
from app.services.ml_predictor import (
    predict_next_hour,
    predict_next_24_hours,
    predict_next_7_days
)
from app.services.final_forecast import get_final_forecast
from app.services.models.registry import list_long_term_models
from app.services.aggregation import (
    get_same_day_history,
    get_monthly_climatology,
    get_yearly_trend,
)
from app.services.weather_fetcher import fetch_openweather_today_summary, fetch_openweather_compare

router = APIRouter(prefix="/weather", tags=["weather"])

# ========================================================================
# PRIMARY ENDPOINT (PRODUCTION LOCKED)
# ========================================================================
# Use this endpoint for frontend integration
# Returns complete forecast with locked schema
# ========================================================================

@router.get("/forecast/{city}")
def forecast(
    city: str,
    long_model: str = Query("b", pattern="^(b|c)$"),
    compare_long_models: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Primary forecast endpoint - PRODUCTION LOCKED
    
    Returns:
    {
      "meta": { "city", "timestamp", "model" },
      "current": { "temp" },
      "hourly": [{ "hour", "temp" } x 24],  # Physics-corrected Model A
      "daily": { "mean": [], "upper": [], "lower": [] }  # Model B climatology
    }
    """
    return get_final_forecast(
        city,
        db,
        long_model=long_model,
        compare_long_models=compare_long_models,
    )


@router.get("/final/{city}")
def final_weather(
    city: str,
    long_model: str = Query("b", pattern="^(b|c)$"),
    compare_long_models: bool = Query(False),
    db: Session = Depends(get_db),
):
    """
    Frontend-facing final forecast endpoint
    
    Returns complete forecast with physics-corrected hourly and 7-day data.
    Alias for /forecast/{city} to match frontend API contract.
    """
    return get_final_forecast(
        city,
        db,
        long_model=long_model,
        compare_long_models=compare_long_models,
    )


@router.get("/models/long-term")
def long_term_models():
    """Lists available long-term models for forecast switching."""
    return {
        "available": list_long_term_models(),
        "default": "b",
    }


@router.get("/trends/{city}")
def trends(city: str, db: Session = Depends(get_db)):
    """
    Read-only historical diagnostics for climate and trends.
    Uses weather table only (no model, no forecast changes).
    """
    today = datetime.now()

    same_day = get_same_day_history(city, db, today.month, today.day)
    monthly = get_monthly_climatology(city, db)
    yearly = get_yearly_trend(city, db)

    return {
        "meta": {
            "city": city,
            "date": today.date().isoformat(),
        },
        "same_day": same_day,
        "monthly": monthly,
        "yearly": yearly,
    }


@router.get("/trends/model/{city}")
def model_trends(
    city: str,
    long_model: str = Query("b", pattern="^(b|c)$"),
    db: Session = Depends(get_db),
):
    """
    Model-aware trend diagnostics.
    Uses historical trends as baseline and applies a model-dependent shift
    so the trends panel reflects the selected long-term model behavior.
    """
    today = datetime.now()

    same_day_hist = get_same_day_history(city, db, today.month, today.day)
    monthly_hist = get_monthly_climatology(city, db)
    yearly_hist = get_yearly_trend(city, db)

    forecast = get_final_forecast(city, db, long_model=long_model)
    daily = forecast.get("daily", {})
    daily_mean = [float(v) for v in daily.get("mean", [])]

    if not monthly_hist or not daily_mean:
        return {
            "meta": {
                "city": city,
                "date": today.date().isoformat(),
                "long_model": long_model,
                "source": "historical_fallback",
            },
            "same_day": same_day_hist,
            "monthly": monthly_hist,
            "yearly": yearly_hist,
        }

    current_month_avg = None
    for row in monthly_hist:
        if int(row["month"]) == int(today.month):
            current_month_avg = float(row["avg_temp"])
            break
    if current_month_avg is None:
        current_month_avg = float(monthly_hist[-1]["avg_temp"])

    model_week_mean = float(mean(daily_mean))
    shift = model_week_mean - current_month_avg

    monthly_model = []
    for row in monthly_hist:
        m = int(row["month"])
        dist = min((m - today.month) % 12, (today.month - m) % 12)
        weight = max(0.25, 1.0 - 0.08 * dist)
        adjusted = float(row["avg_temp"]) + shift * weight
        monthly_model.append({"month": m, "avg_temp": round(adjusted, 2)})

    yearly_model = []
    if yearly_hist:
        for row in yearly_hist:
            adjusted = float(row["avg_temp"]) + shift
            yearly_model.append({"year": int(row["year"]), "avg_temp": round(adjusted, 2)})

    same_day_model = []
    for row in same_day_hist:
        adjusted = float(row["avg_temp"]) + shift
        same_day_model.append({"year": int(row["year"]), "avg_temp": round(adjusted, 2)})

    return {
        "meta": {
            "city": city,
            "date": today.date().isoformat(),
            "long_model": long_model,
            "source": "model_adjusted",
            "shift": round(shift, 3),
        },
        "same_day": same_day_model,
        "monthly": monthly_model,
        "yearly": yearly_model,
    }


@router.get("/openweather/today/{city}")
def openweather_today(city: str):
    """Returns today's OpenWeather forecast summary (avg/high/low)."""
    try:
        return fetch_openweather_today_summary(city)
    except Exception:
        return {
            "city": city,
            "today_key": datetime.now().strftime("%Y-%m-%d"),
            "samples": 0,
            "mean": None,
            "upper": None,
            "lower": None,
        }


@router.get("/openweather/compare/{city}")
def openweather_compare(city: str):
    """Returns OpenWeather compare payload (current, hourly, daily)."""
    try:
        return fetch_openweather_compare(city)
    except Exception:
        return {
            "city": city,
            "current": {"temp": None},
            "hourly": [],
            "daily": {
                "mean": [],
                "upper": [],
                "lower": [],
                "labels": [],
            },
        }


# ========================================================================
# LEGACY ENDPOINTS (Individual model components)
# ========================================================================
# Keep for debugging/testing, but use /forecast/{city} for production
# ========================================================================

@router.get("/current/{city}")
def current(city: str, db: Session = Depends(get_db)):
    """Legacy endpoint: Current temperature only"""
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
        "temperature": float(row.temperature),
        "recorded_at": row.recorded_at.isoformat()
    }


@router.get("/predict/1h/{city}")
def predict_1h(city: str):
    """Legacy endpoint: Next hour prediction only"""
    return {"city": city, "temp": predict_next_hour(city)}


@router.get("/predict/24h/{city}")
def predict_24h(city: str):
    """Legacy endpoint: 24h hourly predictions (raw array)"""
    return {"city": city, "temps": predict_next_24_hours(city)}


@router.get("/predict/7d/{city}")
def predict_7d(city: str):
    """Legacy endpoint: 7-day predictions (raw Model B output)"""
    return {"city": city, "temps": predict_next_7_days(city)}
