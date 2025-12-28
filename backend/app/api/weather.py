from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.db.deps import get_db
from backend.app.models.weather import Weather

router = APIRouter(prefix="/weather", tags=["weather"])

@router.get("/hourly/{city}")
def get_hourly(city: str, db: Session = Depends(get_db)):
    rows = (
        db.query(Weather)
        .filter(Weather.city == city)
        .order_by(Weather.recorded_at.desc())
        .limit(24)
        .all()
    )
    return rows
