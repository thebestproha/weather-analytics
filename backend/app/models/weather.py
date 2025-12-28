from sqlalchemy import Column, Integer, String, Float, DateTime
from backend.app.db.database import Base
from datetime import datetime

class Weather(Base):
    __tablename__ = "weather"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String, index=True)
    temperature = Column(Float)
    humidity = Column(Integer)
    pressure = Column(Integer)
    wind_speed = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
