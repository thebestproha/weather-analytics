from apscheduler.schedulers.background import BackgroundScheduler
from backend.app.db.database import SessionLocal
from backend.app.services.weather_fetcher import fetch_and_store

CITIES = [
    "Chennai",
    "Delhi",
    "Mumbai",
    "Bengaluru",
    "Hyderabad",
    "Kolkata"
]

def collect_weather():
    db = SessionLocal()
    try:
        for city in CITIES:
            fetch_and_store(city, db)
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(collect_weather, "interval", hours=1)
    scheduler.start()
