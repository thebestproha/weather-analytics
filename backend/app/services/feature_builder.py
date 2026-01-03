import numpy as np
import pandas as pd
from sqlalchemy.orm import Session
from backend.app.db.database import SessionLocal
from backend.app.models.weather import Weather
from backend.app.models.weather_features import WeatherFeatures
from math import sin,cos,pi

def build_features():
    db:Session=SessionLocal()

    cities=[c[0] for c in db.query(Weather.city).distinct().all()]

    for city in cities:
        rows=db.query(Weather)\
            .filter(Weather.city==city)\
            .order_by(Weather.recorded_at)\
            .all()

        if len(rows)<48:
            continue

        df=pd.DataFrame([{
            "time":r.recorded_at,
            "temp":r.temperature,
            "humidity":r.humidity,
            "pressure":r.pressure,
            "wind":r.wind_speed
        } for r in rows])

        df.set_index("time",inplace=True)
        df=df.asfreq("H")
        df=df.ffill().dropna()

        df["temp_lag_1"]=df["temp"].shift(1)
        df["temp_lag_3"]=df["temp"].shift(3)
        df["temp_lag_6"]=df["temp"].shift(6)
        df["temp_lag_12"]=df["temp"].shift(12)
        df["temp_lag_24"]=df["temp"].shift(24)

        df=df.dropna()

        for t,row in df.iterrows():
            h=t.hour
            doy=t.timetuple().tm_yday

            wf=WeatherFeatures(
                city=city,
                recorded_at=t,
                temp=row["temp"],
                humidity=row["humidity"],
                pressure=row["pressure"],
                wind_speed=row["wind"],
                temp_lag_1=row["temp_lag_1"],
                temp_lag_3=row["temp_lag_3"],
                temp_lag_6=row["temp_lag_6"],
                temp_lag_12=row["temp_lag_12"],
                temp_lag_24=row["temp_lag_24"],
                hour=h,
                day=t.day,
                month=t.month,
                sin_hour=sin(2*pi*h/24),
                cos_hour=cos(2*pi*h/24),
                sin_doy=sin(2*pi*doy/365),
                cos_doy=cos(2*pi*doy/365)
            )
            db.add(wf)

        db.commit()
        print(f"[FEATURES] {city} done")

    db.close()
