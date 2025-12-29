import requests
from datetime import datetime
from backend.app.models.weather import Weather

API_KEY = "d491158cb11df0224f1c208ac4f35f10"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def fetch_and_store(city, db, lat=None, lon=None):
    if lat is not None and lon is not None:
        params = {
            "lat": lat,
            "lon": lon,
            "appid": API_KEY,
            "units": "metric"
        }
    else:
        params = {
            "q": city,
            "appid": API_KEY,
            "units": "metric"
        }

    r = requests.get(BASE_URL, params=params, timeout=10)
    d = r.json()

    if r.status_code != 200 or "main" not in d:
        print(f"[API ERROR] {city}: {d}")
        return None

    w = Weather(
        city=city,
        temperature=d["main"]["temp"],
        humidity=d["main"]["humidity"],
        pressure=d["main"]["pressure"],
        wind_speed=d["wind"]["speed"],
        recorded_at=datetime.utcnow(),
        source="LIVE"
    )

    db.add(w)
    return w
