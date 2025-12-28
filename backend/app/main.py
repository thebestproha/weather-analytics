from fastapi import FastAPI
from backend.app.db.database import Base, engine
from backend.app.api.weather import router as weather_router
from backend.app.services.scheduler import start_scheduler

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Weather Analytics Backend")

app.include_router(weather_router)

@app.on_event("startup")
def startup():
    start_scheduler()

@app.get("/")
def root():
    return {"status": "Backend running"}
