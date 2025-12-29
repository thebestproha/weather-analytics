import requests
from datetime import datetime
from backend.app.models.weather import Weather

API_KEY="PUT_YOUR_KEY_HERE"
BASE_URL="https://api.openweathermap.org/data/2.5/weather"

def fetch_and_store(city,db):
    r=requests.get(BASE_URL,params={
        "q":city,
        "appid":API_KEY,
        "units":"metric"
    },timeout=10)

    d=r.json()
    if r.status_code!=200 or "main" not in d:
        return None

    ts=datetime.utcnow().replace(minute=0,second=0,microsecond=0)

    exists=db.query(Weather).filter(
        Weather.city==city,
        Weather.recorded_at==ts
    ).first()

    if exists:
        return exists

    w=Weather(
        city=city,
        temperature=d["main"]["temp"],
        humidity=d["main"]["humidity"],
        pressure=d["main"]["pressure"],
        wind_speed=d["wind"]["speed"],
        recorded_at=ts
    )

    db.add(w)
    db.commit()
    db.refresh(w)
    return w
