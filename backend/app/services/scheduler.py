from apscheduler.schedulers.background import BackgroundScheduler
from backend.app.db.session import get_db
from backend.app.services.weather_fetcher import fetch_and_store

CITIES=["Chennai","Bangalore","Delhi","Mumbai","Kolkata"]

def start_scheduler():
    scheduler=BackgroundScheduler()

    def job():
        for city in CITIES:
            db=next(get_db())
            fetch_and_store(city,db)

    scheduler.add_job(job,"interval",hours=1)
    scheduler.start()
