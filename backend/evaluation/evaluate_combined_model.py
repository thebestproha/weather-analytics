import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    median_absolute_error,
    precision_recall_curve,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.database import SessionLocal
from app.models.weather_features import WeatherFeatures
from app.services.aggregation import get_daily_weather
from app.services.train_model_c import _build_dataset


FEATURES = [
    "temp_lag_1",
    "temp_lag_3",
    "temp_lag_6",
    "temp_lag_24",
    "temp_lag_72",
    "temp_lag_168",
    "temp_mean_72h",
    "temp_mean_168h",
    "temp_trend_72h",
    "temp_trend_168h",
    "delta_1h",
    "delta_24h",
    "roll_mean_24h",
    "roll_std_24h",
    "sin_hour",
    "cos_hour",
    "sin_doy",
]


def load_short_term_validation(city: str, model_path: Path):
    db = SessionLocal()
    try:
        rows = (
            db.query(WeatherFeatures)
            .filter(WeatherFeatures.city == city)
            .order_by(WeatherFeatures.recorded_at)
            .all()
        )
    finally:
        db.close()

    x_data = []
    y_data = []
    for r in rows:
        vals = [getattr(r, f) for f in FEATURES]
        if any(v is None for v in vals) or r.temp is None:
            continue
        x_data.append(vals)
        y_data.append(float(r.temp))

    if len(x_data) < 500:
        raise RuntimeError(
            f"Insufficient short-term samples for {city}: {len(x_data)} (need >= 500)"
        )

    x_all = np.array(x_data, dtype=float)
    y_all = np.array(y_data, dtype=float)

    split = int(len(x_all) * 0.8)
    x_val = x_all[split:]
    y_val = y_all[split:]

    model = joblib.load(model_path)
    y_pred = model.predict(x_val).astype(float)

    return y_val, y_pred


def load_long_term_validation(city: str, artifact_path: Path):
    db = SessionLocal()
    try:
        daily = get_daily_weather(city, db)
    finally:
        db.close()

    x_all, y_all = _build_dataset(daily)
    if x_all is None or len(x_all) < 80:
        raise RuntimeError(
            f"Insufficient long-term supervised samples for {city}: {0 if x_all is None else len(x_all)}"
        )

    split = int(len(x_all) * 0.8)
    x_val = x_all[split:]
    y_val = y_all[split:]

    artifact = joblib.load(artifact_path)
    model = artifact["model"]
    y_pred = model.predict(x_val).astype(float)

    return y_val.reshape(-1), y_pred.reshape(-1)


def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray):
    mse = mean_squared_error(y_true, y_pred)
    rmse = float(np.sqrt(mse))
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": rmse,
        "r2": float(r2_score(y_true, y_pred)),
        "mape": float(mean_absolute_percentage_error(y_true, y_pred)),
        "medae": float(median_absolute_error(y_true, y_pred)),
        "mean_bias": float(np.mean(y_pred - y_true)),
    }


def compute_classification_metrics(y_true: np.ndarray, y_pred: np.ndarray):
    threshold = float(np.quantile(y_true, 0.75))

    y_true_cls = (y_true >= threshold).astype(int)
    y_pred_cls = (y_pred >= threshold).astype(int)

    metrics = {
        "threshold_temp": threshold,
        "accuracy": float(accuracy_score(y_true_cls, y_pred_cls)),
        "precision": float(precision_score(y_true_cls, y_pred_cls, zero_division=0)),
        "recall": float(recall_score(y_true_cls, y_pred_cls, zero_division=0)),
        "f1": float(f1_score(y_true_cls, y_pred_cls, zero_division=0)),
        "support_positive": int(y_true_cls.sum()),
        "support_total": int(len(y_true_cls)),
    }

    unique_classes = np.unique(y_true_cls)
    if unique_classes.size == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_true_cls, y_pred))
        metrics["pr_auc"] = float(average_precision_score(y_true_cls, y_pred))
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None

    return metrics, y_true_cls, y_pred_cls


def save_curve_artifacts(y_true_cls, y_scores, outdir: Path):
    unique_classes = np.unique(y_true_cls)
    if unique_classes.size < 2:
        return None, None

    fpr, tpr, roc_thresh = roc_curve(y_true_cls, y_scores)
    pr_prec, pr_rec, pr_thresh = precision_recall_curve(y_true_cls, y_scores)

    roc_csv = outdir / "roc_curve.csv"
    with open(roc_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fpr", "tpr", "threshold"])
        for i in range(len(fpr)):
            thr = roc_thresh[i] if i < len(roc_thresh) else ""
            w.writerow([float(fpr[i]), float(tpr[i]), thr])

    pr_csv = outdir / "pr_curve.csv"
    with open(pr_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["precision", "recall", "threshold"])
        for i in range(len(pr_prec)):
            thr = pr_thresh[i] if i < len(pr_thresh) else ""
            w.writerow([float(pr_prec[i]), float(pr_rec[i]), thr])

    plt.figure(figsize=(7, 5))
    plt.plot(fpr, tpr, label="ROC")
    plt.plot([0, 1], [0, 1], "--", alpha=0.6)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("Combined Model ROC Curve")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    roc_png = outdir / "roc_curve.png"
    plt.savefig(roc_png, dpi=130)
    plt.close()

    plt.figure(figsize=(7, 5))
    plt.plot(pr_rec, pr_prec, label="PR")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Combined Model Precision-Recall Curve")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    pr_png = outdir / "pr_curve.png"
    plt.savefig(pr_png, dpi=130)
    plt.close()

    return roc_csv.name, pr_csv.name


def save_confusion(y_true_cls, y_pred_cls, outdir: Path):
    cm = confusion_matrix(y_true_cls, y_pred_cls, labels=[0, 1])
    cm_path = outdir / "confusion_matrix.csv"
    with open(cm_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["", "pred_0", "pred_1"])
        w.writerow(["true_0", int(cm[0, 0]), int(cm[0, 1])])
        w.writerow(["true_1", int(cm[1, 0]), int(cm[1, 1])])


def save_predictions_csv(y_true, y_pred, outdir: Path):
    p = outdir / "combined_predictions.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "y_true", "y_pred", "error"])
        for i, (t, p_) in enumerate(zip(y_true, y_pred)):
            w.writerow([i, float(t), float(p_), float(p_ - t)])


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate combined weather model (short-term + long-term) as one system."
    )
    parser.add_argument("--city", default="Chennai", help="City to evaluate")
    parser.add_argument(
        "--outdir",
        default="evaluation/results",
        help="Output root folder for evaluation artifacts",
    )
    args = parser.parse_args()

    backend_root = BACKEND_ROOT
    models_dir = backend_root / "app" / "models"

    short_model_path = models_dir / f"{args.city}_gbm.joblib"
    long_model_path = models_dir / f"{args.city}_model_c_et.joblib"

    if not short_model_path.exists():
        raise FileNotFoundError(f"Short-term model file not found: {short_model_path}")
    if not long_model_path.exists():
        raise FileNotFoundError(f"Long-term model file not found: {long_model_path}")

    y_short_true, y_short_pred = load_short_term_validation(args.city, short_model_path)
    y_long_true, y_long_pred = load_long_term_validation(args.city, long_model_path)

    y_true = np.concatenate([y_short_true, y_long_true])
    y_pred = np.concatenate([y_short_pred, y_long_pred])

    reg = compute_regression_metrics(y_true, y_pred)
    cls, y_true_cls, y_pred_cls = compute_classification_metrics(y_true, y_pred)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = (backend_root / args.outdir).resolve()
    outdir = out_root / f"{args.city.lower()}_combined_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)

    save_predictions_csv(y_true, y_pred, outdir)
    save_confusion(y_true_cls, y_pred_cls, outdir)
    save_curve_artifacts(y_true_cls, y_pred, outdir)

    summary = {
        "meta": {
            "city": args.city,
            "generated_at": datetime.now().isoformat(),
            "short_model": short_model_path.name,
            "long_model": long_model_path.name,
            "combined_samples": int(len(y_true)),
            "short_samples": int(len(y_short_true)),
            "long_samples": int(len(y_long_true)),
        },
        "regression": reg,
        "classification": cls,
    }

    with open(outdir / "metrics_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    txt_lines = [
        "COMBINED MODEL EVALUATION",
        "==========================",
        f"City: {args.city}",
        f"Generated: {summary['meta']['generated_at']}",
        f"Short samples: {summary['meta']['short_samples']}",
        f"Long samples: {summary['meta']['long_samples']}",
        f"Combined samples: {summary['meta']['combined_samples']}",
        "",
        "Regression metrics:",
        f"- MAE: {reg['mae']:.4f}",
        f"- RMSE: {reg['rmse']:.4f}",
        f"- R2: {reg['r2']:.4f}",
        f"- MAPE: {reg['mape']:.4f}",
        f"- MedAE: {reg['medae']:.4f}",
        f"- Mean bias: {reg['mean_bias']:.4f}",
        "",
        "Classification metrics (high-temp event threshold):",
        f"- Threshold temp: {cls['threshold_temp']:.4f}",
        f"- Accuracy: {cls['accuracy']:.4f}",
        f"- Precision: {cls['precision']:.4f}",
        f"- Recall: {cls['recall']:.4f}",
        f"- F1: {cls['f1']:.4f}",
        f"- ROC-AUC: {cls['roc_auc'] if cls['roc_auc'] is not None else 'N/A'}",
        f"- PR-AUC: {cls['pr_auc'] if cls['pr_auc'] is not None else 'N/A'}",
        "",
        f"Results folder: {outdir}",
    ]
    with open(outdir / "metrics_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print("\n".join(txt_lines))


if __name__ == "__main__":
    main()
