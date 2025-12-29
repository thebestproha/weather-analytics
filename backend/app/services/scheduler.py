from apscheduler.schedulers.background import BackgroundScheduler
from backend.app.db.deps import get_db
from backend.app.services.weather_fetcher import fetch_and_store
from backend.app.constants.cities import CITIES

def job():
    db=next(get_db())
    for c in CITIES:
        fetch_and_store(c,db)
    db.close()

def start_scheduler():
    s=BackgroundScheduler()
    s.add_job(job,"interval",hours=1)
    s.start()
