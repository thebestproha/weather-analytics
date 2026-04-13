from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.weather import router as weather_router
from app.db.database import Base, engine
from app.services.scheduler import start_scheduler


app = FastAPI(title="Weather Analytics System")

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
ASSETS_DIR = STATIC_DIR / "assets"
REPO_ROOT = APP_DIR.parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
COMPARE_DIR = REPO_ROOT / "weather_model_b_ml_clone"

if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")
if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")
if COMPARE_DIR.exists():
    app.mount("/compare-static", StaticFiles(directory=str(COMPARE_DIR)), name="compare-static")

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
    return FileResponse(STATIC_DIR / "portal.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/app/set1")
def app_set1():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/app/set2")
def app_set2():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/app/compare")
def app_compare():
    return FileResponse(FRONTEND_DIR / "index.html")
