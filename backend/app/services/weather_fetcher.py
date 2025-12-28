import requests
from datetime import datetime
from backend.app.models.weather import Weather

API_KEY = "d491158cb11df0224f1c208ac4f35f10"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

def fetch_and_store(city, db):
    print(f"Fetching weather for {city}")

    r = requests.get(
        BASE_URL,
        params={
            "q": city,
            "appid": API_KEY,
            "units": "metric"
        },
        timeout=10
    )

    data = r.json()

    if r.status_code != 200:
        print("API ERROR:", data)
        return None

    w = Weather(
        city=city,
        temperature=data["main"]["temp"],
        humidity=data["main"]["humidity"],
        pressure=data["main"]["pressure"],
        wind_speed=data["wind"]["speed"],
        recorded_at=datetime.utcnow()
    )

    db.add(w)
    db.commit()
    db.refresh(w)

    print(f"Stored weather for {city}")
    return w
