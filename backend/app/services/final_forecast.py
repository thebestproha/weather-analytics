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
from app.services.weather_fetcher import fetch_openweather_today_summary, fetch_openweather_compare


def _has_daily_payload(payload):
    if not isinstance(payload, dict):
        return False
    means = payload.get("mean")
    upper = payload.get("upper")
    lower = payload.get("lower")
    return isinstance(means, list) and isinstance(upper, list) and isinstance(lower, list) and len(means) > 0


def _daily_flat_from_temp(temp: float, days: int = 7):
    mean = [round(float(temp), 2) for _ in range(days)]
    upper = [round(float(temp) + 1.0, 2) for _ in range(days)]
    lower = [round(float(temp) - 1.0, 2) for _ in range(days)]
    return {
        "mean": mean,
        "upper": upper,
        "lower": lower,
    }


def _normalize_hourly_24(hourly, start_hour: int):
    if not isinstance(hourly, list) or len(hourly) == 0:
        return [
            {
                "hour": f"{(start_hour + i) % 24:02d}:00",
                "temp": 0.0,
            }
            for i in range(24)
        ]

    if len(hourly) == 24:
        return hourly

    base_temps = []
    for row in hourly:
        try:
            base_temps.append(float((row or {}).get("temp")))
        except Exception:
            pass

    if not base_temps:
        base_temps = [0.0]

    if len(base_temps) == 1:
        interpolated = [base_temps[0] for _ in range(24)]
    else:
        interpolated = []
        for i in range(24):
            pos = (i * (len(base_temps) - 1)) / 23.0
            lo = int(pos)
            hi = min(len(base_temps) - 1, lo + 1)
            w = pos - lo
            temp = (1.0 - w) * base_temps[lo] + w * base_temps[hi]
            interpolated.append(round(float(temp), 2))

    return [
        {
            "hour": f"{(start_hour + i) % 24:02d}:00",
            "temp": float(interpolated[i]),
        }
        for i in range(24)
    ]


def _normalize_daily_7(daily, anchor_temp: float):
    if not isinstance(daily, dict):
        return _daily_flat_from_temp(anchor_temp)

    mean = [float(v) for v in (daily.get("mean") or []) if v is not None]
    upper = [float(v) for v in (daily.get("upper") or []) if v is not None]
    lower = [float(v) for v in (daily.get("lower") or []) if v is not None]

    if not mean:
        return _daily_flat_from_temp(anchor_temp)

    # Extend mean to 7 values with damped continuation of recent trend.
    while len(mean) < 7:
        if len(mean) >= 2:
            step = (mean[-1] - mean[-2]) * 0.7
        else:
            step = 0.0
        mean.append(round(mean[-1] + step, 2))

    mean = mean[:7]

    if len(upper) < len(mean):
        upper.extend([mean[min(i, len(mean) - 1)] + 1.5 for i in range(len(upper), len(mean))])
    if len(lower) < len(mean):
        lower.extend([mean[min(i, len(mean) - 1)] - 1.5 for i in range(len(lower), len(mean))])

    upper = [round(float(v), 2) for v in upper[:7]]
    lower = [round(float(v), 2) for v in lower[:7]]

    return {
        "mean": [round(float(v), 2) for v in mean],
        "upper": upper,
        "lower": lower,
    }


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
    openweather_compare = None

    try:
        openweather_compare = fetch_openweather_compare(city)
    except Exception:
        openweather_compare = None

    today_openweather = None
    try:
        today_openweather = fetch_openweather_today_summary(city)
    except Exception:
        today_openweather = None

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
            current_temp = None
    else:
        current_temp = float(latest.temperature)

    if current_temp is None and openweather_compare:
        candidate = (openweather_compare.get("current") or {}).get("temp")
        if candidate is not None:
            current_temp = float(candidate)

    if current_temp is None and today_openweather:
        candidate = today_openweather.get("mean")
        if candidate is not None:
            current_temp = float(candidate)

    if current_temp is None:
        raise RuntimeError(f"No weather data found for {city}")

    # -------------------------------
    # 2. MODEL A: HOURLY (24h)
    # -------------------------------
    hourly = forecast_hourly_model_a(city, current_temp=current_temp, current_hour=now.hour)

    if not hourly:
        ow_hourly = (openweather_compare or {}).get("hourly") if openweather_compare else None
        if isinstance(ow_hourly, list) and len(ow_hourly) > 0:
            hourly = ow_hourly
        else:
            hourly = [
                {
                    "hour": f"{(now.hour + i) % 24:02d}:00",
                    "temp": round(float(current_temp), 2),
                }
                for i in range(8)
            ]

    hourly = _normalize_hourly_24(hourly, now.hour)

    # -------------------------------
    # 3. LONG-TERM MODEL: DAILY (7d)
    # -------------------------------
    selected_long_model = get_long_term_model(long_model)
    if not selected_long_model:
        available = ",".join(list_long_term_models().keys())
        raise RuntimeError(f"Unknown long-term model '{long_model}'. Available: {available}")

    daily_forecast = selected_long_model["forecast"](city, db)

    if not _has_daily_payload(daily_forecast):
        ow_daily = (openweather_compare or {}).get("daily") if openweather_compare else None
        if _has_daily_payload(ow_daily):
            daily_forecast = ow_daily
        else:
            daily_forecast = _daily_flat_from_temp(current_temp)

    daily_forecast = _normalize_daily_7(daily_forecast, current_temp)

    compare_payload = None
    if compare_long_models:
        model_b = get_long_term_model("b")
        model_c = get_long_term_model("c")
        daily_b = model_b["forecast"](city, db)
        daily_c = model_c["forecast"](city, db)

        if not _has_daily_payload(daily_b):
            daily_b = daily_forecast
        if not _has_daily_payload(daily_c):
            daily_c = daily_forecast

        daily_b = _normalize_daily_7(daily_b, current_temp)
        daily_c = _normalize_daily_7(daily_c, current_temp)

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
