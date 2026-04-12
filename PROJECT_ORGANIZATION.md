# Project Organization (Safe Layout)

This file explains what is core runtime code vs optional folders.

## Core runtime (do not move)
- `backend/app/`
- `frontend/`
- `weather.db`
- `run_all_pages.ps1`
- `backend/app/models/`
- `weather_model_b_ml_clone/side_by_side_compare.html` (used by `run_all_pages.ps1`)

## Training and evaluation
- `backend/app/services/train_models.py` (Model A)
- `backend/app/services/train_model_c.py` (Model C)
- `backend/evaluation/` scripts

## Optional but useful
- `backend/debug/` (diagnostics and test scripts)
- `presentation_pack/` and `presentation_pack.zip` (demo delivery bundle)
- `weather_model_b_ml_clone/` (Model B ML clone experiments + compare page)

## Archived duplicates
- `archive/duplicates/backend_backend/`

This was moved from `backend/backend/` because it duplicated model artifact structure and was not part of active runtime imports.

## Notes
- Use `.venv/` as the only Python environment for this workspace.
- Do not move `weather_model_b_ml_clone/` unless launcher script is updated.
