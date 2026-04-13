import requests
import os
from datetime import datetime, timedelta, timezone
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

    url = (
        f"{FORECAST_URL}"
        f"?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_KEY}"
    )

    r = requests.get(url, timeout=10)
    r.raise_for_status()
    payload = r.json()

    tz_offset = int(payload.get("city", {}).get("timezone", 0) or 0)
    city_now = datetime.now(timezone.utc) + timedelta(seconds=tz_offset)
    today_key = city_now.strftime("%Y-%m-%d")

    current_temp = None
    current_temp_max = None
    current_temp_min = None
    try:
        current_url = (
            f"{BASE_URL}"
            f"?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_KEY}"
        )
        current_resp = requests.get(current_url, timeout=10)
        current_resp.raise_for_status()
        current_payload = current_resp.json()
        current_val = current_payload.get("main", {}).get("temp")
        current_max = current_payload.get("main", {}).get("temp_max")
        current_min = current_payload.get("main", {}).get("temp_min")
        if current_val is not None:
            current_temp = float(current_val)
        if current_max is not None:
            current_temp_max = float(current_max)
        if current_min is not None:
            current_temp_min = float(current_min)
    except Exception:
        current_temp = None
        current_temp_max = None
        current_temp_min = None

    temps = []
    highs = []
    lows = []
    for item in payload.get("list", []):
        dt_unix = item.get("dt")
        day_key = None
        if dt_unix is not None:
            try:
                dt_local = datetime.fromtimestamp(int(dt_unix), tz=timezone.utc) + timedelta(seconds=tz_offset)
                day_key = dt_local.strftime("%Y-%m-%d")
            except Exception:
                day_key = None

        if day_key is None:
            dt_txt = item.get("dt_txt")
            if isinstance(dt_txt, str) and len(dt_txt) >= 10:
                day_key = dt_txt[:10]

        if day_key == today_key:
            main = item.get("main", {})
            temp = main.get("temp")
            temp_max = main.get("temp_max")
            temp_min = main.get("temp_min")
            if temp is not None:
                temps.append(float(temp))
            if temp_max is not None:
                highs.append(float(temp_max))
            if temp_min is not None:
                lows.append(float(temp_min))

    # Include current-condition high/low from OpenWeather weather API.
    if current_temp_max is not None:
        highs.append(float(current_temp_max))
    if current_temp_min is not None:
        lows.append(float(current_temp_min))
    if current_temp is not None:
        temps.append(float(current_temp))

    if not temps:
        # No same-day forecast slots in feed. Use current observation fields.
        if current_temp is not None:
            high = current_temp_max if current_temp_max is not None else current_temp
            low = current_temp_min if current_temp_min is not None else current_temp
            return {
                "city": city,
                "today_key": today_key,
                "samples": 1,
                "mean": round(current_temp, 2),
                "upper": round(high, 2),
                "lower": round(low, 2),
            }

        return {
            "city": city,
            "today_key": today_key,
            "samples": 0,
            "mean": None,
            "upper": None,
            "lower": None,
        }

    mean_val = sum(temps) / len(temps)
    upper_val = max(highs) if highs else max(temps)
    lower_val = min(lows) if lows else min(temps)
    return {
        "city": city,
        "today_key": today_key,
        "samples": len(temps),
        "mean": round(mean_val, 2),
        "upper": round(upper_val, 2),
        "lower": round(lower_val, 2),
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
    tz_offset = int(payload.get("city", {}).get("timezone", 0) or 0)

    entries = payload.get("list", [])
    hourly = []
    for item in entries[:8]:
        dt_unix = item.get("dt")
        if dt_unix is not None:
            try:
                dt_local = datetime.fromtimestamp(int(dt_unix), tz=timezone.utc) + timedelta(seconds=tz_offset)
                hour_label = dt_local.strftime("%H:%M")
            except Exception:
                hour_label = "--:--"
        else:
            dt_txt = item.get("dt_txt") or ""
            hour_label = dt_txt[11:16] if len(dt_txt) >= 16 else "--:--"
        temp = item.get("main", {}).get("temp")
        if temp is not None:
            hourly.append({"hour": hour_label, "temp": float(temp)})

    by_day = {}
    for item in entries:
        dt_unix = item.get("dt")
        day_key = None
        if dt_unix is not None:
            try:
                dt_local = datetime.fromtimestamp(int(dt_unix), tz=timezone.utc) + timedelta(seconds=tz_offset)
                day_key = dt_local.strftime("%Y-%m-%d")
            except Exception:
                day_key = None

        if day_key is None:
            dt_txt = item.get("dt_txt")
            if isinstance(dt_txt, str) and len(dt_txt) >= 10:
                day_key = dt_txt[:10]

        if not day_key:
            continue

        temp = item.get("main", {}).get("temp")
        if temp is None:
            continue
        by_day.setdefault(day_key, []).append(float(temp))

    city_now = datetime.now(timezone.utc) + timedelta(seconds=tz_offset)
    today_key = city_now.strftime("%Y-%m-%d")
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
    try:
        current_url = (
            f"{BASE_URL}"
            f"?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_KEY}"
        )
        current_resp = requests.get(current_url, timeout=10)
        current_resp.raise_for_status()
        current_payload = current_resp.json()
        current_val = current_payload.get("main", {}).get("temp")
        if current_val is not None:
            current_temp = float(current_val)
    except Exception:
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
