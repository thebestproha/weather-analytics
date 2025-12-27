import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
from backend.app.models.weather import Weather
from backend.app.db.session import get_db

def train_and_predict(city, hours_ahead=24):
    db = next(get_db())

    rows = db.query(Weather)\
        .filter(Weather.city == city)\
        .order_by(Weather.recorded_at)\
        .all()

    if len(rows) < 10:
        return {"error": "not enough data"}

    times = np.array([
        (r.recorded_at - rows[0].recorded_at).total_seconds()/3600
        for r in rows
    ]).reshape(-1,1)

    temps = np.array([r.temperature for r in rows])

    model = LinearRegression()
    model.fit(times, temps)

    last_time = times[-1][0]
    future_times = np.array(
        [[last_time + i] for i in range(1, hours_ahead+1)]
    )

    preds = model.predict(future_times)

    now = rows[-1].recorded_at
    result = []

    for i,p in enumerate(preds):
        result.append({
            "time": (now + timedelta(hours=i+1)).isoformat(),
            "predicted_temperature": round(float(p),2)
        })

    return result
