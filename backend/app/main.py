from fastapi import FastAPI
from backend.app.db.database import Base,engine
from backend.app.api.weather import router as weather_router
from backend.app.models.weather import Weather

app=FastAPI(title="Weather Analytics API",version="1.0.0")

Base.metadata.create_all(bind=engine)
app.include_router(weather_router)

@app.get("/")
def health():
    return {"status":"ok"}
