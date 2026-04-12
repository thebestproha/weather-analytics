# Weather Analytics

## Deploy On Render

This repository includes a Render blueprint for the backend API.

### Files Added For Render

- `render.yaml`
- `backend/requirements-render.txt`

### Deploy Steps

1. Push this repository to GitHub.
2. In Render, choose **New +** -> **Blueprint**.
3. Select this GitHub repository.
4. Render will detect `render.yaml` and create `weather-analytics-api`.
5. Deploy.

### Service Details

- Root directory: `backend`
- Build command: `pip install -r requirements-render.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### Environment Variables (Render)

- `OPENWEATHER_API_KEY` (required)
- `WEATHERAPI_KEY` (optional, only used by current weather override helper)

### Notes

- The app currently uses SQLite (`weather.db`).
- Model artifacts for all cities are not yet available; only Chennai is fully trained now.
- Unsupported cities should show a "Coming soon" UI state in frontend screens.

