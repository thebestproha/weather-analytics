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

# Backward compatibility (do not remove)
def fetch_and_store_current(city: str):
    return fetch_openweather_and_store(city)
