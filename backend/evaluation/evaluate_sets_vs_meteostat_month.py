import argparse
import csv
import json
import os
import sqlite3
import sys
from datetime import date, datetime, timedelta
from math import pi, sin
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
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

from app.services.city_profiles import CITY_PROFILE
from app.services.models.model_c import _build_feature_vector

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


def calc_trend(series):
    vals = np.asarray(series, dtype=float)
    if len(vals) < 2 or np.isnan(vals).all():
        return np.nan
    x = np.arange(len(vals), dtype=float)
    try:
        return float(np.polyfit(x, vals, 1)[0])
    except Exception:
        return np.nan


def build_feature_frame(hourly_temp: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"temp": hourly_temp.astype(float)})

    df["temp_lag_1"] = df["temp"].shift(1)
    df["temp_lag_3"] = df["temp"].shift(3)
    df["temp_lag_6"] = df["temp"].shift(6)
    df["temp_lag_24"] = df["temp"].shift(24)
    df["temp_lag_72"] = df["temp"].shift(72)
    df["temp_lag_168"] = df["temp"].shift(168)

    df["delta_1h"] = df["temp"] - df["temp_lag_1"]
    df["delta_24h"] = df["temp"] - df["temp_lag_24"]

    df["roll_mean_24h"] = df["temp"].rolling(24).mean()
    df["roll_std_24h"] = df["temp"].rolling(24).std()

    df["temp_mean_72h"] = df["temp"].rolling(72).mean()
    df["temp_mean_168h"] = df["temp"].rolling(168).mean()

    df["temp_trend_72h"] = df["temp"].rolling(72).apply(calc_trend, raw=False)
    df["temp_trend_168h"] = df["temp"].rolling(168).apply(calc_trend, raw=False)

    hours = df.index.hour
    doys = df.index.dayofyear
    df["sin_hour"] = np.sin(2 * np.pi * hours / 24.0)
    df["cos_hour"] = np.cos(2 * np.pi * hours / 24.0)
    df["sin_doy"] = np.sin(2 * np.pi * doys / 365.0)

    return df


def forecast_model_a_24h(model, feature_row: pd.Series, current_temp: float, current_hour: int = 0):
    x = np.array([[float(feature_row[f]) for f in FEATURES]], dtype=float)

    model_predictions = [float(model.predict(x)[0]) for _ in range(24)]
    model_mean = float(np.mean(model_predictions))
    model_anomalies = [p - model_mean for p in model_predictions]

    def physics_diurnal_shape(hour):
        peak_hour = 13.5
        phase_shift = peak_hour - 6.0
        amplitude = 3.5
        return amplitude * sin(2 * pi * (hour - phase_shift) / 24.0)

    PHYSICS_WEIGHT = 0.80
    MODEL_WEIGHT = 0.20

    blended_anomalies = []
    for h in range(24):
        target_hour = (current_hour + h) % 24
        physics_anomaly = physics_diurnal_shape(target_hour)
        blended = PHYSICS_WEIGHT * physics_anomaly + MODEL_WEIGHT * model_anomalies[h]
        blended_anomalies.append(blended)

    baseline = float(current_temp) - blended_anomalies[0]
    raw_forecast = [baseline + a for a in blended_anomalies]

    forecast = [float(current_temp)]
    for h in range(1, 24):
        candidate = raw_forecast[h]
        prev = forecast[h - 1]
        delta = candidate - prev
        if delta > 1.2:
            candidate = prev + 1.2
        elif delta < -1.2:
            candidate = prev - 1.2
        forecast.append(float(round(candidate, 2)))

    return forecast


def model_b_7d_from_base(base_temp: float, city: str):
    profile = CITY_PROFILE.get(city, {"amp": 2.5, "trend": 0.02})

    climo = []
    for d in range(7):
        seasonal = profile["trend"] * 24 * d
        weekly = profile["amp"] * sin(2 * pi * d / 7)
        climo.append(base_temp + seasonal + weekly)

    days = list(climo)
    if len(days) >= 4:
        trend = ((days[1] - days[0]) + (days[2] - days[1])) / 2.0
        decay = [1.0, 0.8, 0.6, 0.4]
        for idx, d in enumerate(range(3, min(7, 3 + len(decay)))):
            blended = 0.65 * climo[d] + 0.35 * (days[d - 1] + trend * decay[idx])
            if blended < days[d - 1] - 1.0:
                blended = days[d - 1] - 1.0
            days[d] = blended

    return [float(round(v, 2)) for v in days]


def model_c_day1_from_history(city: str, history_daily_means: list[float], forecast_date: date, b_7d: list[float]):
    model_path = BACKEND_ROOT / "app" / "models" / f"{city}_model_c_et.joblib"
    artifact = joblib.load(model_path)

    x = _build_feature_vector(history_daily_means, forecast_date)
    if x is None:
        return float(b_7d[0])

    pred = artifact["model"].predict(x.reshape(1, -1))[0]
    means = [float(v) for v in pred[:7]]

    calibration = artifact.get("calibration", {}) if isinstance(artifact, dict) else {}
    bias = calibration.get("bias_by_horizon") or []
    if len(bias) >= 7:
        means = [means[i] - float(bias[i]) for i in range(7)]

    blend_weight_b = 0.60
    means = [
        (1.0 - blend_weight_b) * means[i] + blend_weight_b * float(b_7d[i])
        for i in range(7)
    ]

    return float(round(means[0], 2))


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray):
    mse = mean_squared_error(y_true, y_pred)
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(y_true, y_pred)),
        "mape": float(mean_absolute_percentage_error(y_true, y_pred)),
        "mean_bias": float(np.mean(y_pred - y_true)),
    }


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray):
    threshold = float(np.quantile(y_true, 0.75))
    y_true_bin = (y_true >= threshold).astype(int)
    y_pred_bin = (y_pred >= threshold).astype(int)

    out = {
        "threshold": threshold,
        "accuracy": float(accuracy_score(y_true_bin, y_pred_bin)),
        "precision": float(precision_score(y_true_bin, y_pred_bin, zero_division=0)),
        "recall": float(recall_score(y_true_bin, y_pred_bin, zero_division=0)),
        "f1": float(f1_score(y_true_bin, y_pred_bin, zero_division=0)),
        "support_positive": int(y_true_bin.sum()),
        "support_total": int(len(y_true_bin)),
    }

    if len(np.unique(y_true_bin)) == 2:
        out["roc_auc"] = float(roc_auc_score(y_true_bin, y_pred))
        out["pr_auc"] = float(average_precision_score(y_true_bin, y_pred))
    else:
        out["roc_auc"] = None
        out["pr_auc"] = None

    return out, y_true_bin


def tolerance_metrics(y_true: np.ndarray, y_pred: np.ndarray):
    err = np.abs(y_pred - y_true)
    bias = float(np.mean(y_pred - y_true))

    corrected = y_pred - bias
    err_corrected = np.abs(corrected - y_true)

    def hit(e, t):
        return float(np.mean(e <= t))

    return {
        "within_0_5c": hit(err, 0.5),
        "within_1_0c": hit(err, 1.0),
        "within_1_5c": hit(err, 1.5),
        "mean_abs_error": float(np.mean(err)),
        "bias": bias,
        "bias_corrected_within_1_0c": hit(err_corrected, 1.0),
    }


def save_curves(outdir: Path, y_true_bin: np.ndarray, y_pred_1: np.ndarray, y_pred_2: np.ndarray):
    if len(np.unique(y_true_bin)) < 2:
        return

    fpr1, tpr1, thr1 = roc_curve(y_true_bin, y_pred_1)
    fpr2, tpr2, thr2 = roc_curve(y_true_bin, y_pred_2)

    with open(outdir / "roc_set1_a_plus_b.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fpr", "tpr", "threshold"])
        for i in range(len(fpr1)):
            w.writerow([float(fpr1[i]), float(tpr1[i]), thr1[i] if i < len(thr1) else ""])

    with open(outdir / "roc_set2_a_plus_c.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fpr", "tpr", "threshold"])
        for i in range(len(fpr2)):
            w.writerow([float(fpr2[i]), float(tpr2[i]), thr2[i] if i < len(thr2) else ""])

    plt.figure(figsize=(7, 5))
    plt.plot(fpr1, tpr1, label="Set1: A+B", linestyle="--", marker="o", markersize=3)
    plt.plot(fpr2, tpr2, label="Set2: A+C", linestyle="-", marker="s", markersize=3)
    plt.plot([0, 1], [0, 1], "--", alpha=0.4)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve vs Meteostat (Monthly Backtest)")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(outdir / "roc_comparison.png", dpi=130)
    plt.close()

    p1, r1, _ = precision_recall_curve(y_true_bin, y_pred_1)
    p2, r2, _ = precision_recall_curve(y_true_bin, y_pred_2)

    plt.figure(figsize=(7, 5))
    plt.plot(r1, p1, label="Set1: A+B", linestyle="--", marker="o", markersize=3)
    plt.plot(r2, p2, label="Set2: A+C", linestyle="-", marker="s", markersize=3)
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("PR Curve vs Meteostat (Monthly Backtest)")
    plt.grid(alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(outdir / "pr_comparison.png", dpi=130)
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Backtest Set1(A+B) and Set2(A+C) for a month against Meteostat observations."
    )
    parser.add_argument("--city", default="Chennai")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=2)
    parser.add_argument("--outdir", default="evaluation/results")
    args = parser.parse_args()

    city = args.city

    month_start = date(args.year, args.month, 1)
    next_month = date(args.year + (1 if args.month == 12 else 0), 1 if args.month == 12 else args.month + 1, 1)
    month_end = next_month - timedelta(days=1)

    fetch_start = month_start - timedelta(days=220)
    fetch_end = month_end + timedelta(days=1)

    db_path = BACKEND_ROOT.parent / "weather.db"
    if not db_path.exists():
        raise RuntimeError(f"weather.db not found: {db_path}")

    con = sqlite3.connect(str(db_path))
    try:
        q = """
        select recorded_at, temperature
        from weather
        where city = ?
          and source like 'Meteostat%'
          and recorded_at >= ?
          and recorded_at < ?
        order by recorded_at
        """
        df_raw = pd.read_sql_query(
            q,
            con,
            params=(
                city,
                datetime.combine(fetch_start, datetime.min.time()).isoformat(sep=" "),
                datetime.combine(fetch_end + timedelta(days=1), datetime.min.time()).isoformat(sep=" "),
            ),
        )

        if df_raw.empty:
            q_months = """
            select substr(recorded_at, 1, 7) as ym, count(*) as n
            from weather
            where city = ? and source like 'Meteostat%'
            group by ym
            order by ym desc
            limit 12
            """
            months = pd.read_sql_query(q_months, con, params=(city,))
            raise RuntimeError(
                f"No Meteostat rows available for {city} in requested window {fetch_start} to {fetch_end}. "
                f"Recent Meteostat months in DB: {months.to_dict(orient='records')}"
            )
    finally:
        con.close()

    df_raw["recorded_at"] = pd.to_datetime(df_raw["recorded_at"])
    df_raw = df_raw.dropna(subset=["temperature"]).sort_values("recorded_at")
    hourly_temp = df_raw.set_index("recorded_at")["temperature"].astype(float)

    full_idx = pd.date_range(start=hourly_temp.index.min(), end=hourly_temp.index.max(), freq="h")
    hourly_temp = hourly_temp.reindex(full_idx).interpolate(limit_direction="both")

    features = build_feature_frame(hourly_temp)

    model_a = joblib.load(BACKEND_ROOT / "app" / "models" / f"{city}_gbm.joblib")

    target_days = pd.date_range(month_start, month_end, freq="D")

    daily_obs_series = hourly_temp.loc[
        (hourly_temp.index >= pd.Timestamp(month_start))
        & (hourly_temp.index < pd.Timestamp(next_month))
    ].resample("D").mean()

    y_true_daily = []
    y_set1_daily = []
    y_set2_daily = []
    rows = []

    history_daily_series = hourly_temp.resample("D").mean()

    for day_ts in target_days:
        anchor = pd.Timestamp(day_ts)
        if anchor not in features.index:
            continue

        row = features.loc[anchor]
        if any(pd.isna(row[f]) for f in FEATURES):
            continue

        if day_ts not in daily_obs_series.index or pd.isna(daily_obs_series.loc[day_ts]):
            continue

        current_temp = float(row["temp"])
        a24 = forecast_model_a_24h(model_a, row, current_temp=current_temp, current_hour=0)
        a_day = float(np.mean(a24))

        b7 = model_b_7d_from_base(float(row["roll_mean_24h"]), city)
        b_day = float(b7[0])

        hist_daily_vals = history_daily_series.loc[history_daily_series.index < day_ts].dropna().tolist()
        c_day = model_c_day1_from_history(city, hist_daily_vals, day_ts.date(), b7)

        set1 = float((a_day + b_day) / 2.0)
        set2 = float((a_day + c_day) / 2.0)
        actual = float(daily_obs_series.loc[day_ts])

        y_true_daily.append(actual)
        y_set1_daily.append(set1)
        y_set2_daily.append(set2)

        rows.append(
            {
                "date": day_ts.date().isoformat(),
                "actual_meteostat_daily_mean": round(actual, 4),
                "set1_pred_a_plus_b": round(set1, 4),
                "set2_pred_a_plus_c": round(set2, 4),
                "model_a_daily_mean": round(a_day, 4),
                "model_b_day1": round(b_day, 4),
                "model_c_day1": round(c_day, 4),
            }
        )

    if len(y_true_daily) < 8:
        raise RuntimeError(
            f"Too few valid daily backtest points for {city} {args.year}-{args.month:02d}: {len(y_true_daily)}"
        )

    y_true = np.array(y_true_daily, dtype=float)
    y1 = np.array(y_set1_daily, dtype=float)
    y2 = np.array(y_set2_daily, dtype=float)

    reg1 = regression_metrics(y_true, y1)
    reg2 = regression_metrics(y_true, y2)

    cls1, y_true_bin = classification_metrics(y_true, y1)
    cls2, _ = classification_metrics(y_true, y2)

    tol1 = tolerance_metrics(y_true, y1)
    tol2 = tolerance_metrics(y_true, y2)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = (BACKEND_ROOT / args.outdir).resolve()
    outdir = out_root / f"{city.lower()}_meteostat_eval_{args.year}{args.month:02d}_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)

    with open(outdir / "daily_backtest_predictions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    save_curves(outdir, y_true_bin, y1, y2)

    summary = {
        "meta": {
            "city": city,
            "year": args.year,
            "month": args.month,
            "target": "meteostat_daily_mean_temperature",
            "samples": int(len(y_true)),
            "set1": "(model_a_daily_mean + model_b_day1) / 2",
            "set2": "(model_a_daily_mean + model_c_day1) / 2",
            "generated_at": datetime.now().isoformat(),
        },
        "set1_a_plus_b": {
            "regression": reg1,
            "classification": cls1,
            "tolerance": tol1,
        },
        "set2_a_plus_c": {
            "regression": reg2,
            "classification": cls2,
            "tolerance": tol2,
        },
    }

    with open(outdir / "metrics_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "METEOSTAT MONTHLY BACKTEST (SET1 VS SET2)",
        "=========================================",
        f"City: {city}",
        f"Month: {args.year}-{args.month:02d}",
        f"Samples: {len(y_true)} days",
        "",
        "Set1 (A+B) Regression:",
        f"- MAE: {reg1['mae']:.4f}",
        f"- RMSE: {reg1['rmse']:.4f}",
        f"- R2: {reg1['r2']:.4f}",
        f"- MAPE: {reg1['mape']:.4f}",
        f"- Mean bias: {reg1['mean_bias']:.4f}",
        "",
        "Set1 (A+B) Classification:",
        f"- Precision: {cls1['precision']:.4f}",
        f"- Recall: {cls1['recall']:.4f}",
        f"- F1: {cls1['f1']:.4f}",
        f"- Accuracy: {cls1['accuracy']:.4f}",
        f"- ROC-AUC: {cls1['roc_auc'] if cls1['roc_auc'] is not None else 'N/A'}",
        f"- PR-AUC: {cls1['pr_auc'] if cls1['pr_auc'] is not None else 'N/A'}",
        "",
        "Set1 (A+B) Tolerance:",
        f"- Within +-1.0C: {tol1['within_1_0c']:.4f}",
        f"- Bias corrected within +-1.0C: {tol1['bias_corrected_within_1_0c']:.4f}",
        "",
        "Set2 (A+C) Regression:",
        f"- MAE: {reg2['mae']:.4f}",
        f"- RMSE: {reg2['rmse']:.4f}",
        f"- R2: {reg2['r2']:.4f}",
        f"- MAPE: {reg2['mape']:.4f}",
        f"- Mean bias: {reg2['mean_bias']:.4f}",
        "",
        "Set2 (A+C) Classification:",
        f"- Precision: {cls2['precision']:.4f}",
        f"- Recall: {cls2['recall']:.4f}",
        f"- F1: {cls2['f1']:.4f}",
        f"- Accuracy: {cls2['accuracy']:.4f}",
        f"- ROC-AUC: {cls2['roc_auc'] if cls2['roc_auc'] is not None else 'N/A'}",
        f"- PR-AUC: {cls2['pr_auc'] if cls2['pr_auc'] is not None else 'N/A'}",
        "",
        "Set2 (A+C) Tolerance:",
        f"- Within +-1.0C: {tol2['within_1_0c']:.4f}",
        f"- Bias corrected within +-1.0C: {tol2['bias_corrected_within_1_0c']:.4f}",
        "",
        f"Results folder: {outdir}",
    ]

    with open(outdir / "metrics_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
