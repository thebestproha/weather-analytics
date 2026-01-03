from sqlalchemy import Column,Integer,Float,String,DateTime,Index
from backend.app.db.database import Base

class WeatherFeatures(Base):
    __tablename__="weather_features"

    id=Column(Integer,primary_key=True,index=True)
    city=Column(String,index=True)
    recorded_at=Column(DateTime,index=True)

    temp=Column(Float)
    humidity=Column(Float)
    pressure=Column(Float)
    wind_speed=Column(Float)

    temp_lag_1=Column(Float)
    temp_lag_3=Column(Float)
    temp_lag_6=Column(Float)
    temp_lag_12=Column(Float)
    temp_lag_24=Column(Float)

    hour=Column(Integer)
    day=Column(Integer)
    month=Column(Integer)

    sin_hour=Column(Float)
    cos_hour=Column(Float)
    sin_doy=Column(Float)
    cos_doy=Column(Float)

    __table_args__=(
        Index("ix_city_time","city","recorded_at"),
    )
