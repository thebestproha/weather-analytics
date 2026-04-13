# Render Replica Profile

This folder locks Render to a local-like snapshot runtime.

## Included runtime data

- `weather.snapshot.sqlite`: snapshot copied from local `weather.db`
- `backend/app/models/Chennai_gbm.joblib`: tracked trained short-term model artifact

## How it is wired

- `WEATHER_DB_PATH=backend/replica/weather.snapshot.sqlite`
- `DISABLE_SCHEDULER=true`

Both are set in `render.yaml` on branch `replica-render-lock`.

## Why this profile exists

This profile is for deterministic behavior that matches local snapshot data and avoids drift from background ingestion differences on Render.

## Updating the snapshot later

From repo root:

```powershell
Copy-Item -Path "weather.db" -Destination "backend/replica/weather.snapshot.sqlite" -Force
```

Then commit and push the updated snapshot file.
