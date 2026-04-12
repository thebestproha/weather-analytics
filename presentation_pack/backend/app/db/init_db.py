from app.db.database import engine, Base

# Import ALL models to register them with Base.metadata
from app.models.weather import Weather
from app.models.weather_features import WeatherFeatures

def init_db():
    """Create all tables defined in models"""
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables created successfully")
    print(f"[DB] Location: {engine.url}")

if __name__ == "__main__":
    init_db()
