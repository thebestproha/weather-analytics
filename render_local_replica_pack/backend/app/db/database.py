from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


def _resolve_db_path():
    override = (os.getenv("WEATHER_DB_PATH") or "").strip()
    default_path = BASE_DIR / "weather.db"

    if override:
        raw = Path(override)
        if raw.is_absolute():
            if raw.exists():
                return raw
            return default_path

        candidates = [
            BASE_DIR / raw,
            BACKEND_DIR / raw,
            Path.cwd() / raw,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Safety fallback: avoid creating a fresh empty DB from a bad env value.
        return default_path

    return default_path


DB_PATH = _resolve_db_path()

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
