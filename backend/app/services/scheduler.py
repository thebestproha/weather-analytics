from apscheduler.schedulers.background import BackgroundScheduler
from backend.app.services.weather_fetcher import fetch_and_store
from backend.app.constants.city_coords import CITY_COORDS
from backend.app.db.database import SessionLocal

scheduler = BackgroundScheduler()

def collect_live_weather():
    db = SessionLocal()
    try:
        for city, (lat, lon) in CITY_COORDS.items():
            fetch_and_store(city=city, lat=lat, lon=lon, db=db)
            print(f"[LIVE] Stored weather for {city}")
        db.commit()
    finally:
        db.close()

def start_scheduler():
    scheduler.add_job(
        collect_live_weather,
        trigger="interval",
        minutes=30,
        id="live_weather_job",
        replace_existing=True
    )
    scheduler.start()
