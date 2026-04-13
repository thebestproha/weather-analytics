from apscheduler.schedulers.background import BackgroundScheduler
import os
from app.services.weather_fetcher import fetch_and_store_current
from app.constants.cities import CITIES

scheduler = BackgroundScheduler()


def start_scheduler():
    """
    Fetch live weather every 10 minutes
    """
    if (os.getenv("DISABLE_SCHEDULER", "").strip().lower() in {"1", "true", "yes", "on"}):
        print("[SCHEDULER] Disabled via DISABLE_SCHEDULER")
        return

    # Prime fresh current weather once at startup so UI does not show stale values.
    fetch_all_cities()

    scheduler.add_job(
        func=fetch_all_cities,
        trigger="interval",
        minutes=10
    )
    scheduler.start()


def fetch_all_cities():
    for city in CITIES:
        try:
            fetch_and_store_current(city)
        except Exception as e:
            print(f"Weather fetch failed for {city}: {e}")
