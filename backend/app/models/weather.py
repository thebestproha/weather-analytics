from sqlalchemy import Column, Integer, Float, String, DateTime
from backend.app.db.database import Base


class Weather(Base):
    __tablename__ = "weather"

    id = Column(Integer, primary_key=True, index=True)

    city = Column(String, index=True)
    temperature = Column(Float, nullable=True)
    humidity = Column(Float, nullable=True)
    pressure = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)

    rainfall = Column(Float, nullable=True)   # ✅ ERA5 + future use
    source = Column(String, nullable=False)   # "ERA5" or "LIVE"

    recorded_at = Column(DateTime, index=True)
