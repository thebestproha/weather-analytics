from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime
from backend.app.db.database import Base

class Weather(Base):
    __tablename__ = "weather"

    id = Column(Integer, primary_key=True)
    city = Column(String, index=True)
    temperature = Column(Float)
    humidity = Column(Integer)
    pressure = Column(Integer)
    wind_speed = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
