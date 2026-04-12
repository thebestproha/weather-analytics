import requests
import os
from datetime import datetime
from app.db.database import SessionLocal
from app.models.weather import Weather
from app.constants.city_coords import CITY_COORDS

OPENWEATHER_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
CITY_ALIASES = {
    "Bangalore": "Bengaluru",
}


def _resolve_city_coords(city: str):
    canonical = CITY_ALIASES.get(city, city)
    coords = CITY_COORDS.get(canonical)
    if not coords:
        raise ValueError(f"Unsupported city: {city}")
    return coords


def _require_openweather_key():
    if not OPENWEATHER_KEY:
        raise RuntimeError("OPENWEATHER_API_KEY is not set")





def fetch_openweather_and_store(city: str):
    _require_openweather_key()
    lat, lon = _resolve_city_coords(city)

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_KEY}"
    )

    r = requests.get(url, timeout=10)
    data = r.json()

    temp = float(data["main"]["temp"])
    humidity = float(data["main"]["humidity"])
    pressure = float(data["main"]["pressure"])
    wind = float(data["wind"]["speed"])
    ts = datetime.utcfromtimestamp(data["dt"])

    db = SessionLocal()
    try:
        row = Weather(
            city=city,
            temperature=temp,
            humidity=humidity,
            pressure=pressure,
            wind_speed=wind,
            rainfall=None,
            source="openweather",          # 🔑 IMPORTANT
            recorded_at=ts
        )
        db.add(row)
        db.commit()
        return row
    finally:
        db.close()


def fetch_openweather_today_summary(city: str):
    _require_openweather_key()
    lat, lon = _resolve_city_coords(city)
    today_key = datetime.now().strftime("%Y-%m-%d")

    url = (
        f"{FORECAST_URL}"
        f"?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_KEY}"
    )

    r = requests.get(url, timeout=10)
    r.raise_for_status()
    payload = r.json()

    temps = []
    for item in payload.get("list", []):
        dt_txt = item.get("dt_txt")
        if isinstance(dt_txt, str) and dt_txt[:10] == today_key:
            temp = item.get("main", {}).get("temp")
            if temp is not None:
                temps.append(float(temp))

    if not temps:
        # Late-day edge case: forecast feed may contain no remaining same-day slots.
        current_url = (
            f"{BASE_URL}"
            f"?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_KEY}"
        )
        current_resp = requests.get(current_url, timeout=10)
        current_resp.raise_for_status()
        current_payload = current_resp.json()
        current_temp = float(current_payload.get("main", {}).get("temp"))

        return {
            "city": city,
            "today_key": today_key,
            "samples": 0,
            "mean": round(current_temp, 2),
            "upper": round(current_temp, 2),
            "lower": round(current_temp, 2),
        }

    mean_val = sum(temps) / len(temps)
    return {
        "city": city,
        "today_key": today_key,
        "samples": len(temps),
        "mean": round(mean_val, 2),
        "upper": round(max(temps), 2),
        "lower": round(min(temps), 2),
    }


def fetch_openweather_compare(city: str):
    """Fetches OpenWeather forecast and returns compare-page friendly payload."""
    _require_openweather_key()
    lat, lon = _resolve_city_coords(city)

    url = (
        f"{FORECAST_URL}"
        f"?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_KEY}"
    )

    r = requests.get(url, timeout=10)
    r.raise_for_status()
    payload = r.json()

    entries = payload.get("list", [])
    hourly = []
    for item in entries[:8]:
        dt_txt = item.get("dt_txt") or ""
        hour_label = dt_txt[11:16] if len(dt_txt) >= 16 else "--:--"
        temp = item.get("main", {}).get("temp")
        if temp is not None:
            hourly.append({"hour": hour_label, "temp": float(temp)})

    by_day = {}
    for item in entries:
        dt_txt = item.get("dt_txt")
        if not isinstance(dt_txt, str) or len(dt_txt) < 10:
            continue
        day_key = dt_txt[:10]
        temp = item.get("main", {}).get("temp")
        if temp is None:
            continue
        by_day.setdefault(day_key, []).append(float(temp))

    today_key = datetime.now().strftime("%Y-%m-%d")
    future_keys = [
        key
        for key in sorted(by_day.keys())
        if key > today_key and len(by_day.get(key, [])) >= 8
    ][:5]

    mean = []
    upper = []
    lower = []
    labels = []
    for idx, key in enumerate(future_keys):
        vals = by_day[key]
        avg = sum(vals) / len(vals)
        weekday = datetime.strptime(key, "%Y-%m-%d").strftime("%a")
        label = f"D{idx + 1} {weekday}"
        if idx == 0:
            label += " (Tomorrow)"

        mean.append(round(avg, 2))
        upper.append(round(max(vals), 2))
        lower.append(round(min(vals), 2))
        labels.append(label)

    current_temp = None
    if entries:
        first_temp = entries[0].get("main", {}).get("temp")
        if first_temp is not None:
            current_temp = float(first_temp)

    return {
        "city": city,
        "current": {"temp": current_temp},
        "hourly": hourly,
        "daily": {
            "mean": mean,
            "upper": upper,
            "lower": lower,
            "labels": labels,
        },
    }

# Backward compatibility (do not remove)
def fetch_and_store_current(city: str):
    return fetch_openweather_and_store(city)
