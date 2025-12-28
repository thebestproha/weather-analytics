from apscheduler.schedulers.background import BackgroundScheduler
from backend.app.constants.cities import CITIES
from backend.app.db.database import SessionLocal
from backend.app.services.weather_fetcher import fetch_and_store

def collect_all():
    db = SessionLocal()
    try:
        for city in CITIES:
            fetch_and_store(city, db)
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(collect_all, "interval", hours=1, id="weather_job")
    scheduler.start()
