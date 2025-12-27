from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.session import get_db
from backend.app.models.weather import Weather
from backend.app.services.weather_fetcher import fetch_and_store

router=APIRouter(prefix="/weather",tags=["weather"])

@router.get("/current/{city}")
def current(city:str,db:Session=Depends(get_db)):
    fetch_and_store(city,db)
    return db.query(Weather)\
        .filter(Weather.city==city)\
        .order_by(Weather.recorded_at.desc())\
        .first()

@router.get("/hourly/{city}")
def hourly(city:str,db:Session=Depends(get_db)):
    return db.query(Weather)\
        .filter(Weather.city==city)\
        .order_by(Weather.recorded_at)\
        .all()

@router.get("/daily/{city}")
def daily(city:str,db:Session=Depends(get_db)):
    return db.query(
        func.date(Weather.recorded_at).label("day"),
        func.avg(Weather.temperature).label("temp")
    ).filter(Weather.city==city)\
     .group_by("day")\
     .order_by("day")\
     .all()

@router.get("/monthly/{city}")
def monthly(city:str,db:Session=Depends(get_db)):
    return db.query(
        func.strftime("%Y-%m",Weather.recorded_at).label("month"),
        func.avg(Weather.temperature).label("temp")
    ).filter(Weather.city==city)\
     .group_by("month")\
     .order_by("month")\
     .all()

@router.get("/yearly/{city}")
def yearly(city:str,db:Session=Depends(get_db)):
    return db.query(
        func.strftime("%Y",Weather.recorded_at).label("year"),
        func.avg(Weather.temperature).label("temp")
    ).filter(Weather.city==city)\
     .group_by("year")\
     .order_by("year")\
     .all()
