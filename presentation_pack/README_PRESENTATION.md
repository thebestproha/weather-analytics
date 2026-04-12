# Weather Project Presentation Pack

## Formal model names

- Model B: Climatology-Driven Long-Range Baseline (Seasonal Statistical Forecaster)
- Model C: Adaptive Trend-Calibrated Long-Range Forecaster (Hybrid ML + Climatology Anchor)

## What is included

- `backend/app/` (API + forecast logic)
- `backend/app/models/Chennai_gbm.joblib` (Model A artifact)
- `backend/app/models/Chennai_model_c_et.joblib` (Model C artifact)
- `weather.db` (local data store)
- `frontend/index.html` (Set 1: A+B page)
- `frontend/index_model_c.html` (Set 2: A+C page)
- `compare/side_by_side_compare.html` (3-way compare page)
- `start_demo.ps1` and `stop_demo.ps1`
- `requirements_demo.txt`

## Quick start on friend's laptop

1. Extract zip.
2. Open PowerShell in this folder.
3. First time setup + run:
   `./start_demo.ps1 -Setup`
4. Next runs:
   `./start_demo.ps1`

## Demo URLs

- Backend: http://127.0.0.1:8000
- Old model page (A+B): http://127.0.0.1:5173/index.html
- New model page (A+C): http://127.0.0.1:5174/index_model_c.html
- 3-way compare: http://127.0.0.1:5180/side_by_side_compare.html

## Stop services

- Run: `./stop_demo.ps1`
