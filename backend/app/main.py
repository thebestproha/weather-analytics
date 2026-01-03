from fastapi import FastAPI
from backend.app.db.database import Base, engine
from backend.app.api.weather import router as weather_router
from backend.app.services.scheduler import start_scheduler
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="Weather Analytics")

Base.metadata.create_all(bind=engine)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(weather_router, prefix="/weather")


@app.on_event("startup")
def startup():
    start_scheduler()



@app.get("/")
def root():
    return {"status": "ok"}
