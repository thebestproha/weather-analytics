import os
import joblib
import numpy as np
from backend.app.db.database import SessionLocal
from backend.app.models.weather_features import WeatherFeatures

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "..", "models")

FEATURE_COLS = [
    "temp",
    "temp_lag_1",
    "temp_lag_3",
    "temp_lag_6",
    "temp_lag_12",
    "temp_lag_24",
    "humidity",
    "pressure",
    "wind_speed",
    "sin_hour",
    "cos_hour",
    "sin_doy",
    "cos_doy"
]




def _load_model(city):
    path = os.path.join(MODEL_DIR, f"{city}.joblib")
    return joblib.load(path)

def _latest_feature_row(city):
    db = SessionLocal()
    row = (
        db.query(WeatherFeatures)
        .filter(WeatherFeatures.city == city)
        .order_by(WeatherFeatures.recorded_at.desc())
        .first()
    )
    db.close()
    if not row:
        raise ValueError("No features found")
    return row

def predict_next_hour(city):
    model = _load_model(city)
    row = _latest_feature_row(city)
    x = np.array([[getattr(row, c) for c in FEATURE_COLS]])
    return float(model.predict(x)[0])

def predict_next_24_hours(city):
    model = _load_model(city)
    row = _latest_feature_row(city)

    # keep a stable base window
    base = {c: getattr(row, c) for c in FEATURE_COLS}

    preds = []
    last_real_temp = base["temp"]

    for _ in range(24):
        x = np.array([[base[c] for c in FEATURE_COLS]])
        y = float(model.predict(x)[0])

        # 🔒 clamp unrealistic jumps
        y = max(min(y, last_real_temp + 1.5), last_real_temp - 1.5)

        preds.append(y)

        # update only SHORT lags
        base["temp_lag_3"] = base["temp_lag_1"]
        base["temp_lag_1"] = y
        base["temp"] = y

        last_real_temp = y

    return preds

def predict_next_7_days(city):
    model = _load_model(city)
    row = _latest_feature_row(city)

    base = {c: getattr(row, c) for c in FEATURE_COLS}

    hourly = []
    last_real_temp = base["temp"]

    for _ in range(168):
        x = np.array([[base[c] for c in FEATURE_COLS]])
        y = float(model.predict(x)[0])

        y = max(min(y, last_real_temp + 1.2), last_real_temp - 1.2)

        hourly.append(y)

        base["temp_lag_3"] = base["temp_lag_1"]
        base["temp_lag_1"] = y
        base["temp"] = y

        last_real_temp = y

    # daily mean
    return [
        float(sum(hourly[i:i+24]) / 24)
        for i in range(0, 168, 24)
    ]
