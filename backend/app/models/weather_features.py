from sqlalchemy import Column, Integer, Float, String, DateTime, Index
from backend.app.db.database import Base

class WeatherFeatures(Base):
    __tablename__ = "weather_features"

    id = Column(Integer, primary_key=True)
    city = Column(String, index=True)
    recorded_at = Column(DateTime, index=True)

    # target
    temp = Column(Float)

    # lags
    temp_lag_1 = Column(Float)
    temp_lag_3 = Column(Float)
    temp_lag_6 = Column(Float)
    temp_lag_24 = Column(Float)
    temp_lag_72 = Column(Float)
    temp_lag_168 = Column(Float)

    # rolling / trend
    temp_mean_72h = Column(Float)
    temp_mean_168h = Column(Float)
    temp_trend_72h = Column(Float)
    temp_trend_168h = Column(Float)

    # momentum
    delta_1h = Column(Float)
    delta_24h = Column(Float)

    # rolling stats
    roll_mean_24h = Column(Float)
    roll_std_24h = Column(Float)

    # seasonality
    sin_hour = Column(Float)
    cos_hour = Column(Float)
    sin_doy = Column(Float)
    cos_doy = Column(Float)

    __table_args__ = (
        Index("ix_city_time", "city", "recorded_at"),
    )
