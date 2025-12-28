from sqlalchemy import func
from datetime import date
from backend.app.models.weather import Weather

def get_daily_weather(city: str, db):
    rows = (
        db.query(
            func.date(Weather.recorded_at).label("day"),
            func.avg(Weather.temperature).label("avg_temp"),
            func.min(Weather.temperature).label("min_temp"),
            func.max(Weather.temperature).label("max_temp"),
            func.avg(Weather.humidity).label("avg_humidity"),
        )
        .filter(Weather.city == city)
        .group_by(func.date(Weather.recorded_at))
        .order_by(func.date(Weather.recorded_at))
        .all()
    )

    return [
        {
            "date": r.day,
            "avg_temp": round(r.avg_temp, 2),
            "min_temp": round(r.min_temp, 2),
            "max_temp": round(r.max_temp, 2),
            "avg_humidity": round(r.avg_humidity, 2),
        }
        for r in rows
    ]
