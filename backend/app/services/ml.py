import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import datetime
from backend.app.db.database import SessionLocal
from backend.app.models.weather import Weather

def train_and_predict(city: str):
    db = SessionLocal()
    try:
        rows = (
            db.query(Weather)
            .filter(Weather.city == city)
            .order_by(Weather.recorded_at.desc())
            .limit(168)
            .all()
        )

        if len(rows) < 24:
            return {"error": "Not enough data"}

        rows = list(reversed(rows))

        df = pd.DataFrame({
            "temp": [r.temperature for r in rows],
            "hour": [r.recorded_at.hour for r in rows],
            "day": [r.recorded_at.weekday() for r in rows],
        })

        df["rolling_mean"] = df["temp"].rolling(6).mean().fillna(method="bfill")
        df["trend"] = df["temp"].diff().fillna(0)

        X = df[["hour", "day", "rolling_mean", "trend"]].values
        y = df["temp"].values

        model = LinearRegression()
        model.fit(X, y)

        now = datetime.utcnow()
        last = df.iloc[-1]

        X_next = np.array([[
            now.hour,
            now.weekday(),
            last["rolling_mean"],
            last["trend"],
        ]])

        pred = model.predict(X_next)[0]

        trend_label = (
            "rising" if last["trend"] > 0.1 else
            "falling" if last["trend"] < -0.1 else
            "stable"
        )

        return {
            "predicted_temperature": round(float(pred), 2),
            "trend": trend_label,
            "trained_on_hours": len(df),
        }

    finally:
        db.close()
