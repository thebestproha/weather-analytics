from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.weather import router as weather_router
from app.db.database import Base, engine
from app.services.scheduler import start_scheduler


app = FastAPI(title="Weather Analytics System")

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(weather_router)

@app.on_event("startup")
def startup():
    start_scheduler()

@app.get("/")
def root():
    return {"status": "ok"}
