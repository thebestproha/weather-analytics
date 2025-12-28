from backend.app.services.weather_fetcher import fetch_and_store
from backend.app.db.database import SessionLocal

def backfill_city(city, hours=48):
    db = SessionLocal()
    try:
        for _ in range(hours):
            fetch_and_store(city, db)
    finally:
        db.close()
