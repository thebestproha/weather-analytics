import requests, os
from datetime import datetime
from backend.app.models.weather import Weather

API_KEY = os.getenv("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def fetch_and_store(city, db):
    r = requests.get(BASE_URL, params={
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    })

    d = r.json()

    if r.status_code != 200 or "main" not in d:
        print("Weather API error:", d)
        return None

    w = Weather(
        city=city,
        temperature=d["main"]["temp"],
        humidity=d["main"]["humidity"],
        pressure=d["main"]["pressure"],
        wind_speed=d["wind"]["speed"],
        recorded_at=datetime.utcnow()
    )

    db.add(w)
    db.commit()
    db.refresh(w)   # 🔑 THIS LINE FIXES `{}`

    return w
