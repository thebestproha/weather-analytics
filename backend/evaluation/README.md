# Combined Model Evaluation

This folder evaluates the weather stack as a single system:
- Short-term: Model A (GBM hourly)
- Long-term: Model C (7-day daily)

The script creates unified metrics and artifacts:
- Regression: MAE, RMSE, R2, MAPE, MedAE
- Classification-style event metrics on unified predictions: Precision, Recall, F1, Accuracy, ROC-AUC, PR-AUC
- Curves: ROC and Precision-Recall PNG files

## Run

From `backend`:

```powershell
& "e:/prabanjan/projects/weather x/weather-copy/.venv/Scripts/python.exe" evaluation/evaluate_combined_model.py --city Chennai
```

Evaluate against OpenWeather target (Set1=A+B vs Set2=A+C):

```powershell
& "e:/prabanjan/projects/weather x/weather-copy/.venv/Scripts/python.exe" evaluation/evaluate_sets_vs_openweather.py --city Chennai
```

Optional:

```powershell
& "e:/prabanjan/projects/weather x/weather-copy/.venv/Scripts/python.exe" evaluation/evaluate_combined_model.py --city Chennai --outdir evaluation/results
```

## Output

A timestamped result folder is created under `evaluation/results/` containing:
- `metrics_summary.json`
- `metrics_summary.txt`
- `combined_predictions.csv`
- `roc_curve.csv`
- `pr_curve.csv`
- `roc_curve.png`
- `pr_curve.png`
- `confusion_matrix.csv`
