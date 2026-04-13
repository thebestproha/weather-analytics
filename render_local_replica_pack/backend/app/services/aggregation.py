from sqlalchemy import extract, func
from app.models.weather import Weather


# ---------------- DAILY (USED BY MODEL B) ----------------

def get_daily_weather(city: str, db):
    rows = (
        db.query(
            func.date(Weather.recorded_at).label("day"),
            func.avg(Weather.temperature).label("avg_temp"),
            func.min(Weather.temperature).label("min_temp"),
            func.max(Weather.temperature).label("max_temp"),
        )
        .filter(Weather.city == city)
        .group_by("day")
        .order_by("day")
        .all()
    )

    out = []
    for r in rows:
        out.append({
            "date": str(r.day),
            "avg_temp": float(r.avg_temp),
            "min_temp": float(r.min_temp),
            "max_temp": float(r.max_temp),
        })

    return out


# ---------------- HOURLY CLIMATOLOGY (USED BY FINAL FORECAST) ----------------

def get_hourly_climatology(city: str, db):
    rows = (
        db.query(
            extract("hour", Weather.recorded_at).label("hour"),
            func.avg(Weather.temperature).label("avg_temp"),
            func.min(Weather.temperature).label("min_temp"),
            func.max(Weather.temperature).label("max_temp"),
        )
        .filter(Weather.city == city)
        .group_by("hour")
        .all()
    )

    hourly = {}
    mins = []
    maxs = []

    for r in rows:
        h = int(r.hour)
        hourly[h] = float(r.avg_temp)
        mins.append(float(r.min_temp))
        maxs.append(float(r.max_temp))

    return {
        "hourly": hourly,
        "daily_min": min(mins),
        "daily_max": max(maxs),
    }


# ---------------- TRENDS (READ-ONLY DIAGNOSTICS) ----------------

def get_same_day_history(city: str, db, month: int, day: int):
    month_str = f"{month:02d}"
    day_str = f"{day:02d}"

    rows = (
        db.query(
            func.strftime("%Y", Weather.recorded_at).label("year"),
            func.avg(Weather.temperature).label("avg_temp"),
        )
        .filter(Weather.city == city)
        .filter(func.strftime("%m", Weather.recorded_at) == month_str)
        .filter(func.strftime("%d", Weather.recorded_at) == day_str)
        .group_by("year")
        .order_by("year")
        .all()
    )

    return [
        {
            "year": int(r.year),
            "avg_temp": float(r.avg_temp),
        }
        for r in rows
    ]


def get_monthly_climatology(city: str, db):
    rows = (
        db.query(
            func.strftime("%m", Weather.recorded_at).label("month"),
            func.avg(Weather.temperature).label("avg_temp"),
        )
        .filter(Weather.city == city)
        .group_by("month")
        .order_by("month")
        .all()
    )

    return [
        {
            "month": int(r.month),
            "avg_temp": float(r.avg_temp),
        }
        for r in rows
    ]


def get_yearly_trend(city: str, db):
    rows = (
        db.query(
            func.strftime("%Y", Weather.recorded_at).label("year"),
            func.avg(Weather.temperature).label("avg_temp"),
        )
        .filter(Weather.city == city)
        .group_by("year")
        .order_by("year")
        .all()
    )

    return [
        {
            "year": int(r.year),
            "avg_temp": float(r.avg_temp),
        }
        for r in rows
    ]
