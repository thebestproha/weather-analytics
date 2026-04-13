from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _resolve_db_path():
    override = (os.getenv("WEATHER_DB_PATH") or "").strip()
    if override:
        raw = Path(override)
        if raw.is_absolute():
            return raw

        candidates = [
            BASE_DIR / raw,
            BACKEND_DIR / raw,
            Path.cwd() / raw,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Fallback to historical behavior if no candidate exists yet.
        return BASE_DIR / raw

    return BASE_DIR / "weather.db"


DB_PATH = _resolve_db_path()

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
