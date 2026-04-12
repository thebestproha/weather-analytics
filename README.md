# Weather Analytics Platform

Production-style weather forecasting platform with:

- FastAPI backend for forecast APIs
- Model A short-term hourly forecasting (GBM + physics shaping)
- Model B and Model C long-term daily forecasting
- Three frontend views (Set 1, Set 2, and compare)
- Render-ready deployment config

## Project Structure

- `backend/`: API, models, services, training, evaluation, tests
- `frontend/`: primary web UI pages
- `weather_model_b_ml_clone/`: three-way comparison page and Set benchmark tools
- `presentation_pack/`: demo-focused packaging of backend + frontend + compare
- `run_all_pages.ps1`: one-command local launcher for API + pages
- `render.yaml`: Render blueprint for backend hosting

## Current Support Status

- Chennai: fully supported (trained artifacts available)
- Other cities: ingest and UI support exist, model support is in progress
- Unsupported city model requests should show a "Coming soon" state in UI

## Tech Stack

- Python, FastAPI, SQLAlchemy, APScheduler
- scikit-learn, numpy, pandas, joblib
- SQLite for local persistence
- Chart.js for frontend charts

## Local Setup (Windows PowerShell)

1. Create and activate virtual environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install backend dependencies.

```powershell
pip install -r backend/requirements.txt
```

3. Optional test dependencies.

```powershell
pip install -r backend/requirements-dev.txt
```

4. Set environment variables in current shell.

```powershell
$env:OPENWEATHER_API_KEY = "<your_openweather_key>"
$env:WEATHERAPI_KEY = "<your_weatherapi_key_optional>"
$env:TOMORROW_API_KEY = "<your_tomorrow_key_if_used>"
```

## Run Locally

Use one command to launch backend + all pages.

```powershell
.\run_all_pages.ps1 -OpenPages
```

The launcher starts:

- API: `http://127.0.0.1:8000`
- Set 1 page: `http://127.0.0.1:5173/index.html`
- Set 2 page: `http://127.0.0.1:5174/index_model_c.html`
- Compare page: `http://127.0.0.1:5180/side_by_side_compare.html`

## API Overview

Base: `http://127.0.0.1:8000/weather`

- `GET /final/{city}`: main frontend forecast endpoint
- `GET /forecast/{city}`: alias of final endpoint
- `GET /models/long-term`: available long-term models
- `GET /trends/{city}`: historical same-day/monthly/yearly trends
- `GET /trends/model/{city}`: model-adjusted trends diagnostics
- `GET /openweather/today/{city}`: OpenWeather today summary

Legacy diagnostics endpoints:

- `GET /current/{city}`
- `GET /predict/1h/{city}`
- `GET /predict/24h/{city}`
- `GET /predict/7d/{city}`

## Model Summary

- Set 1: Model A + Model B
- Set 2: Model A + Model C
- OpenWeather lane in compare view is baseline only

Model details:

- Model A: short-term hourly forecast (GBM + physics-aware shaping)
- Model B: climatology-oriented long-term baseline
- Model C: adaptive long-term model with trained artifact fallback behavior

## Testing

Run smoke tests:

```powershell
pytest backend/tests -q
```

## Render Deployment

This repo includes a Render blueprint.

Files:

- `render.yaml`
- `backend/requirements-render.txt`

Recommended deploy path:

1. Push code to GitHub.
2. In Render, choose `New +` then `Blueprint`.
3. Select this repository.
4. Deploy service `weather-analytics-api`.

Equivalent manual service settings:

- Root Directory: `backend`
- Build Command: `pip install -r requirements-render.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Required environment variables on Render:

- `OPENWEATHER_API_KEY`

Optional variables:

- `WEATHERAPI_KEY`
- `TOMORROW_API_KEY`
- `PYTHON_VERSION` set to `3.11.9`

## Security Notes

- Keep API keys only in environment variables.
- Do not hardcode keys in source files.
- Rotate keys if previously exposed in commit history.

## Troubleshooting

- If city switch shows "Coming soon", that city model is not fully prepared yet.
- If frontend appears stale, relaunch with `-OpenPages` to get cache-busted URLs.
- If API fails on startup, confirm env keys and virtual environment activation.

## Roadmap

- Multi-city model training pipeline completion
- Production-grade secrets management and CI checks
- Optional PostgreSQL migration for cloud persistence

