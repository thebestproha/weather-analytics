# Cleanup and Modularization Plan

## Current Modular Model Layout

- `backend/app/services/models/model_a.py` -> Model A (short-term GBM + physics hourly)
- `backend/app/services/models/model_b.py` -> Model B (long-term climatology)
- `backend/app/services/models/model_c.py` -> Model C (long-term adaptive trend alternative)
- `backend/app/services/models/registry.py` -> model selector (`b` or `c`)

## Seamless Switching

- API default: Model B
- Switch model with query parameter: `long_model=b|c`
- Compare outputs with query parameter: `compare_long_models=true`

Examples:
- `/weather/forecast/Chennai?long_model=b`
- `/weather/forecast/Chennai?long_model=c`
- `/weather/forecast/Chennai?long_model=b&compare_long_models=true`

## Bloat / Optional Archive Candidates

These are not required for runtime serving and can be archived when you want a lean deployment:

1. `backend/debug/` scripts
- Purpose: analysis and diagnostics only.
- Keep for research, archive for production image.

2. `archive/duplicates/backend_backend/app/models/Chennai_gbm.joblib`
- Previously existed at `backend/backend/app/models/Chennai_gbm.joblib`.
- Archived as a duplicate nested artifact path.
- Canonical model location remains `backend/app/models/`.

3. `data/era5/raw/` large historical files
- Needed for retraining/backfill.
- Not needed for API-only runtime.

4. `CLEANUP_PLAN.md` and lock notes
- Documentation files only, safe to keep.

## Suggested Archive Structure

If you want a neat split later, create these folders and move optional files:

- `archive/debug-tools/`
- `archive/legacy-artifacts/`
- `archive/raw-data/`

Do not archive `backend/app/models/` and `weather.db` if you need live predictions.

