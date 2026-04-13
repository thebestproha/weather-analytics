from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[3]
_db_override = (os.getenv("WEATHER_DB_PATH") or "").strip()
if _db_override:
    override_path = Path(_db_override)
    DB_PATH = override_path if override_path.is_absolute() else (BASE_DIR / override_path)
else:
    DB_PATH = BASE_DIR / "weather.db"

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
