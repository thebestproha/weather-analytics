import joblib
import numpy as np
from math import sin, cos, pi
from backend.app.db.database import SessionLocal
from backend.app.models.weather_features import WeatherFeatures
from .city_profiles import CITY_PROFILE

FEATURES = [
    "temp_lag_1","temp_lag_3","temp_lag_6","temp_lag_24",
    "temp_lag_72","temp_lag_168",
    "delta_1h","delta_24h",
    "roll_mean_24h","roll_std_24h",
    "sin_hour","cos_hour","sin_doy"
]

# ---------- helpers ----------
def _latest(city):
    db = SessionLocal()
    r = (
        db.query(WeatherFeatures)
        .filter(WeatherFeatures.city == city)
        .order_by(WeatherFeatures.recorded_at.desc())
        .first()
    )
    db.close()
    return r

def _model(city):
    return joblib.load(f"backend/app/models/{city}_gbm.joblib")

# ---------- 1 HOUR ----------
def predict_next_hour(city):
    r = _latest(city)
    if not r:
        return None
    x = np.array([[getattr(r, f) for f in FEATURES]])
    return round(float(_model(city).predict(x)[0]), 2)

# ---------- 24 HOURS ----------
def predict_next_24_hours(city):
    r = _latest(city)
    if not r:
        return []

    model = _model(city)
    profile = CITY_PROFILE.get(city, {"amp": 3, "trend": 0.05})
    base = r.temp

    preds = []
    for h in range(24):
        x = np.array([[getattr(r, f) for f in FEATURES]])
        ml_delta = float(model.predict(x)[0])

        diurnal = profile["amp"] * sin(2 * pi * (h - 6) / 24)
        trend = profile["trend"] * h

        temp = base + ml_delta + diurnal + trend

        # realistic clamp
        temp = max(base - 6, min(base + 6, temp))

        preds.append(round(temp, 2))

    return preds

# ---------- 7 DAYS ----------
def predict_next_7_days(city):
    r = _latest(city)
    if not r:
        return {"mean": [], "upper": [], "lower": []}

    profile = CITY_PROFILE.get(city, {"amp": 2, "trend": 0.1})
    base = r.roll_mean_24h or r.temp

    mean = []
    for d in range(7):
        seasonal = profile["trend"] * 24 * d
        weekly = profile["amp"] * sin(2 * pi * d / 7)
        mean.append(round(base + seasonal + weekly, 2))

    return {
        "mean": mean,
        "upper": [round(v + 2, 2) for v in mean],
        "lower": [round(v - 2, 2) for v in mean]
    }
