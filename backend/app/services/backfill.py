from backend.app.db.database import SessionLocal
from backend.app.services.weather_fetcher import fetch_and_store
from datetime import timedelta, datetime
import time

def backfill_city(city, hours=24):
    db = SessionLocal()
    try:
        for i in range(hours):
            fetch_and_store(city, db)
            time.sleep(1)
    finally:
        db.close()
