import pandas as pd
from math import sin,cos,pi
from sqlalchemy.orm import Session
from backend.app.db.database import SessionLocal
from backend.app.models.weather import Weather
from backend.app.models.weather_features import WeatherFeatures

def build_features():
    db:Session=SessionLocal()

    cities=[c[0] for c in db.query(Weather.city).distinct().all()]

    for city in cities:
        rows=db.query(Weather)\
            .filter(Weather.city==city)\
            .order_by(Weather.recorded_at)\
            .all()

        if len(rows)<200:
            continue

        df=pd.DataFrame([{
            "time":r.recorded_at,
            "temp":r.temperature
        } for r in rows])

        df.set_index("time",inplace=True)
        df=df.asfreq("h").ffill().dropna()

        # lags
        df["temp_lag_1"]=df["temp"].shift(1)
        df["temp_lag_3"]=df["temp"].shift(3)
        df["temp_lag_6"]=df["temp"].shift(6)
        df["temp_lag_24"]=df["temp"].shift(24)
        df["temp_lag_72"]=df["temp"].shift(72)
        df["temp_lag_168"]=df["temp"].shift(168)

        # momentum
        df["delta_1h"]=df["temp"]-df["temp_lag_1"]
        df["delta_24h"]=df["temp"]-df["temp_lag_24"]

        # rolling stats
        df["roll_mean_24h"]=df["temp"].rolling(24).mean()
        df["roll_std_24h"]=df["temp"].rolling(24).std()

        df=df.dropna()

        for t,r in df.iterrows():
            h=t.hour
            doy=t.timetuple().tm_yday

            wf=WeatherFeatures(
                city=city,
                recorded_at=t,
                temp=r.temp,

                temp_lag_1=r.temp_lag_1,
                temp_lag_3=r.temp_lag_3,
                temp_lag_6=r.temp_lag_6,
                temp_lag_24=r.temp_lag_24,
                temp_lag_72=r.temp_lag_72,
                temp_lag_168=r.temp_lag_168,

                delta_1h=r.delta_1h,
                delta_24h=r.delta_24h,

                roll_mean_24h=r.roll_mean_24h,
                roll_std_24h=r.roll_std_24h,

                sin_hour=sin(2*pi*h/24),
                cos_hour=cos(2*pi*h/24),
                sin_doy=sin(2*pi*doy/365),
                cos_doy=cos(2*pi*doy/365)
            )
            db.add(wf)

        db.commit()
        print(f"[FEATURES] {city} done")

    db.close()

if __name__=="__main__":
    build_features()
