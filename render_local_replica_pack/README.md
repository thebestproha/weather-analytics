# Render Local Replica Pack

This folder is a self-contained runtime copy of the local app state.

Included:

- Backend app code: `backend/app`
- Frontend pages: `frontend/`
- Compare page: `weather_model_b_ml_clone/side_by_side_compare.html`
- Local DB snapshot: `weather.db`
- Trained model artifacts in `backend/app/models/`

## Local run from this pack

```powershell
Set-Location render_local_replica_pack/backend
pip install -r requirements-render.txt
$env:DISABLE_SCHEDULER = "true"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Render setup using this pack only

Use `render_local_replica_pack/render.yaml` (or set equivalent values in Render UI):

- Root Directory: `render_local_replica_pack/backend`
- Build Command: `pip install -r requirements-render.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env Vars:
  - `PYTHON_VERSION=3.11.9`
  - `WEATHER_DB_PATH=../weather.db`
  - `DISABLE_SCHEDULER=true`
  - `OPENWEATHER_API_KEY=<your-key>`

`DISABLE_SCHEDULER=true` keeps the replica deterministic and prevents drift from background ingestion.
