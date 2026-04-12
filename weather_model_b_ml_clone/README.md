# Model B ML Clone

This folder lives inside the weather project as a standalone utility.

## Goal
Create a named ML long-term model that mimics current Model B climatology behavior as closely as possible.

## Model Name
`Model B-ML Mimic (MultiOutput GBR)`

## Files
- `train_model_b_ml_clone.py`: trains and saves the ML clone model.
- `predict_model_b_ml_clone.py`: inference utility with same output schema (`mean`, `upper`, `lower`).
- `compare_with_project_model_b.py`: compares clone vs deterministic Model B formula for real city inputs.

## Quick Run
1. From project root, train:
   - `.\.venv\Scripts\python.exe weather_model_b_ml_clone\train_model_b_ml_clone.py`
2. From project root, compare on real cities:
   - `.\.venv\Scripts\python.exe weather_model_b_ml_clone\compare_with_project_model_b.py`

## Notes
- This is a pure ML surrogate trained to reproduce current Model B outputs.
- No production forecast path is modified by this utility.
