# backend/app/services/final_forecast.py
"""
LOCKED FINAL FORECAST - PRODUCTION SCHEMA
==========================================
API returns physics-corrected predictions from ml_predictor.
No blending, no smoothing, no climatology override.

Flow: API → final_forecast → ml_predictor (physics-corrected)
"""

from datetime import datetime
from app.models.weather import Weather
from app.models.weather_features import WeatherFeatures
from app.services.models.model_a import forecast_hourly_model_a
from app.services.models.registry import get_long_term_model, list_long_term_models
from app.services.weather_fetcher import fetch_openweather_today_summary


def get_final_forecast(city: str, db, long_model: str = "b", compare_long_models: bool = False):
    """
    Final forecast API endpoint - returns locked schema
    
    Schema:
    {
      "meta": { "city", "timestamp", "model" },
      "current": { "temp" },
      "hourly": [{ "hour", "temp" } x 24],  # Physics-corrected from Model A
      "daily": { "mean": [7 values] }       # Climatology from Model B
    }
    """
    now = datetime.now()

    # -------------------------------
    # 1. CURRENT TEMPERATURE
    # -------------------------------
    # Try live weather first (source="live"), fallback to Meteostat
    latest = (
        db.query(Weather)
        .filter(Weather.city == city)
        .order_by(Weather.recorded_at.desc())
        .first()
    )

    if not latest:
        # Fallback: use latest from weather_features table
        latest_features = (
            db.query(WeatherFeatures)
            .filter(WeatherFeatures.city == city)
            .order_by(WeatherFeatures.recorded_at.desc())
            .first()
        )
        if latest_features:
            current_temp = float(latest_features.temp)
        else:
            raise RuntimeError(f"No weather data found for {city}")
    else:
        current_temp = float(latest.temperature)

    # -------------------------------
    # 2. MODEL A: HOURLY (24h)
    # -------------------------------
    hourly = forecast_hourly_model_a(city, current_temp=current_temp, current_hour=now.hour)

    if not hourly:
        raise RuntimeError(f"Model A prediction failed for {city}")

    # -------------------------------
    # 3. LONG-TERM MODEL: DAILY (7d)
    # -------------------------------
    selected_long_model = get_long_term_model(long_model)
    if not selected_long_model:
        available = ",".join(list_long_term_models().keys())
        raise RuntimeError(f"Unknown long-term model '{long_model}'. Available: {available}")

    daily_forecast = selected_long_model["forecast"](city, db)

    if not daily_forecast or "mean" not in daily_forecast:
        raise RuntimeError(f"Long-term prediction failed for {city}")

    compare_payload = None
    if compare_long_models:
        model_b = get_long_term_model("b")
        model_c = get_long_term_model("c")
        daily_b = model_b["forecast"](city, db)
        daily_c = model_c["forecast"](city, db)

        diff = [
            round(c - b, 2)
            for b, c in zip(daily_b.get("mean", []), daily_c.get("mean", []))
        ]

        compare_payload = {
            "baseline_model": "b",
            "alternative_model": "c",
            "b": daily_b,
            "c": daily_c,
            "mean_diff_c_minus_b": diff,
        }

    # -------------------------------
    # 4. LOCKED SCHEMA
    # -------------------------------
    today_openweather = None
    try:
        today_openweather = fetch_openweather_today_summary(city)
    except Exception:
        today_openweather = None

    response = {
        "meta": {
            "city": city,
            "timestamp": now.isoformat(),
            "model": f"Model A (GBM + Physics) + {selected_long_model['name']}",
            "long_model_key": long_model.lower(),
        },
        "current": {
            "temp": round(current_temp, 2)
        },
        "hourly": hourly,
        "daily": daily_forecast,  # Contains {"mean": [], "upper": [], "lower": []}
        "today_openweather": today_openweather,
    }

    if compare_payload:
        response["long_model_compare"] = compare_payload

    return response
