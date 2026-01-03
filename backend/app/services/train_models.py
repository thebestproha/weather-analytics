import os
import joblib
import numpy as np
from sqlalchemy.orm import Session
from sklearn.ensemble import GradientBoostingRegressor

from backend.app.db.database import SessionLocal
from backend.app.models.weather_features import WeatherFeatures

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "..",
    "models"
)

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

def train_city(city: str):
    db: Session = SessionLocal()

    rows = (
        db.query(WeatherFeatures)
        .filter(WeatherFeatures.city == city)
        .order_by(WeatherFeatures.recorded_at)
        .all()
    )

    db.close()

    if len(rows) < 200:
        print(f"[SKIP] {city}: not enough data")
        return

    X = []
    y = []

    for r in rows[:-1]:
        X.append([getattr(r, f) for f in FEATURE_COLS])
        y.append(r.temp)

    X = np.array(X)
    y = np.array(y)

    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        random_state=42
    )

    model.fit(X, y)

    os.makedirs(MODEL_DIR, exist_ok=True)
    path = os.path.join(MODEL_DIR, f"{city}.joblib")
    joblib.dump(model, path)

    print(f"[OK] Trained model for {city}")

def main():
    db = SessionLocal()
    cities = [c[0] for c in db.query(WeatherFeatures.city).distinct().all()]
    db.close()

    for city in cities:
        train_city(city)

if __name__ == "__main__":
    main()
