from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timedelta
import random
from backend.app.db.session import get_db
from backend.app.models.weather import Weather

def backfill_city(city, hours=168):
    db = next(get_db())
    now = datetime.utcnow()

    base_temp = 30.0
    base_humidity = 70
    base_pressure = 1012
    base_wind = 3.0

    for i in range(hours):
        w = Weather(
            city=city,
            temperature=base_temp + random.uniform(-2, 2),
            humidity=base_humidity + random.randint(-5, 5),
            pressure=base_pressure + random.randint(-3, 3),
            wind_speed=base_wind + random.uniform(-1, 1),
            recorded_at=now - timedelta(hours=i)
        )
        db.add(w)

    db.commit()
