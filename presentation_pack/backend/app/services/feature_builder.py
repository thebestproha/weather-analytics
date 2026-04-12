import pandas as pd
import numpy as np
from math import sin,cos,pi
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.weather import Weather
from app.models.weather_features import WeatherFeatures

def build_features():
    """
    Build comprehensive ML features from raw weather data
    - Lag features: 1h, 3h, 6h, 24h, 72h, 168h
    - Rolling stats: 6h, 24h, 72h, 168h windows
    - Momentum: 1h and 24h deltas
    - Cyclic encoding: hour-of-day, day-of-year
    """
    db:Session=SessionLocal()

    cities=[c[0] for c in db.query(Weather.city).distinct().all()]
    
    print(f"\n{'='*60}")
    print("BUILDING ML FEATURES")
    print(f"{'='*60}\n")

    for city in cities:
        print(f"Processing {city}...")
        
        rows=db.query(Weather)\
            .filter(Weather.city==city)\
            .order_by(Weather.recorded_at)\
            .all()

        if len(rows)<200:
            print(f"  ⚠️  Insufficient data ({len(rows)} rows), skipping")
            continue

        df=pd.DataFrame([{
            "time":r.recorded_at,
            "temp":r.temperature
        } for r in rows])

        df.set_index("time",inplace=True)
        df=df.asfreq("h").ffill().dropna()
        
        print(f"  Total hours: {len(df):,}")

        # ========== LAG FEATURES ==========
        df["temp_lag_1"]=df["temp"].shift(1)
        df["temp_lag_3"]=df["temp"].shift(3)
        df["temp_lag_6"]=df["temp"].shift(6)
        df["temp_lag_24"]=df["temp"].shift(24)
        df["temp_lag_72"]=df["temp"].shift(72)
        df["temp_lag_168"]=df["temp"].shift(168)

        # ========== MOMENTUM (DELTAS) ==========
        df["delta_1h"]=df["temp"]-df["temp_lag_1"]
        df["delta_24h"]=df["temp"]-df["temp_lag_24"]

        # ========== ROLLING STATISTICS ==========
        # 6-hour window
        df["roll_mean_6h"]=df["temp"].rolling(6).mean()
        df["roll_std_6h"]=df["temp"].rolling(6).std()
        
        # 24-hour window
        df["roll_mean_24h"]=df["temp"].rolling(24).mean()
        df["roll_std_24h"]=df["temp"].rolling(24).std()
        
        # 72-hour (3-day) window
        df["temp_mean_72h"]=df["temp"].rolling(72).mean()
        df["temp_std_72h"]=df["temp"].rolling(72).std()
        
        # 168-hour (7-day) window
        df["temp_mean_168h"]=df["temp"].rolling(168).mean()
        df["temp_std_168h"]=df["temp"].rolling(168).std()
        
        # ========== TREND FEATURES ==========
        # Linear trend over 72h and 168h windows
        def calc_trend(series):
            x = np.arange(len(series))
            if len(series) < 2 or series.isna().all():
                return np.nan
            try:
                slope = np.polyfit(x, series, 1)[0]
                return slope
            except:
                return np.nan
        
        df["temp_trend_72h"]=df["temp"].rolling(72).apply(calc_trend, raw=False)
        df["temp_trend_168h"]=df["temp"].rolling(168).apply(calc_trend, raw=False)

        # Drop rows with NaN in critical features (due to lag/rolling windows)
        # Drop rows with NaN in critical features (due to lag/rolling windows)
        df=df.dropna()
        
        print(f"  Features computed: {len(df):,} valid rows")
        print(f"  Dropped: {len(rows) - len(df):,} rows (insufficient history)")

        # ========== INSERT INTO DATABASE ==========
        for t,r in df.iterrows():
            h=t.hour
            doy=t.timetuple().tm_yday

            wf=WeatherFeatures(
                city=city,
                recorded_at=t,
                temp=r.temp,

                # Lags
                temp_lag_1=r.temp_lag_1,
                temp_lag_3=r.temp_lag_3,
                temp_lag_6=r.temp_lag_6,
                temp_lag_24=r.temp_lag_24,
                temp_lag_72=r.temp_lag_72,
                temp_lag_168=r.temp_lag_168,

                # Momentum
                delta_1h=r.delta_1h,
                delta_24h=r.delta_24h,

                # Rolling stats
                roll_mean_24h=r.roll_mean_24h,
                roll_std_24h=r.roll_std_24h,
                
                # Long-term rolling
                temp_mean_72h=r.temp_mean_72h,
                temp_mean_168h=r.temp_mean_168h,
                
                # Trends
                temp_trend_72h=r.temp_trend_72h,
                temp_trend_168h=r.temp_trend_168h,

                # Cyclic encoding (preserves periodicity)
                sin_hour=sin(2*pi*h/24),
                cos_hour=cos(2*pi*h/24),
                sin_doy=sin(2*pi*doy/365),
                cos_doy=cos(2*pi*doy/365)
            )
            db.add(wf)

        db.commit()
        print(f"  ✅ {city} features saved ({len(df):,} rows)\n")

    db.close()
    
    print("="*60)
    print("FEATURE ENGINEERING COMPLETE")
    print("="*60 + "\n")

if __name__=="__main__":
    build_features()
