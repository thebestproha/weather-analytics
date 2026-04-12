import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import requests
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.constants.city_coords import CITY_COORDS


def get_openweather_key():
    env_key = os.getenv("OPENWEATHER_KEY")
    if env_key:
        return env_key
    try:
        from app.services.weather_fetcher import OPENWEATHER_KEY

        return OPENWEATHER_KEY
    except Exception as ex:
        raise RuntimeError("OPENWEATHER_KEY not found in env or weather_fetcher.py") from ex


def fetch_project_forecast(api_base: str, city: str, long_model: str):
    url = f"{api_base.rstrip('/')}/weather/final/{city}?long_model={long_model}"
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    return resp.json()


def fetch_openweather_forecast(city: str, api_key: str):
    if city not in CITY_COORDS:
        raise ValueError(f"City '{city}' not available in CITY_COORDS")

    lat, lon = CITY_COORDS[city]
    url = (
        "https://api.openweathermap.org/data/2.5/forecast"
        f"?lat={lat}&lon={lon}&units=metric&appid={api_key}"
    )
    resp = requests.get(url, timeout=25)
    resp.raise_for_status()
    data = resp.json()
    points = data.get("list", [])
    if len(points) < 2:
        raise RuntimeError("OpenWeather returned insufficient points")
    return points


def build_openweather_hourly_target(points):
    now = datetime.now(timezone.utc)
    base_ts = np.array([int(p["dt"]) for p in points], dtype=float)
    base_temp = np.array([float(p["main"]["temp"]) for p in points], dtype=float)

    target_ts = np.array(
        [
            now.timestamp() + 3600 * h
            for h in range(1, 25)
        ],
        dtype=float,
    )

    # Clamp interpolation bounds to available OpenWeather horizon.
    target_ts = np.clip(target_ts, base_ts.min(), base_ts.max())
    hourly = np.interp(target_ts, base_ts, base_temp)
    return hourly.tolist()


def build_openweather_daily_target(points):
    by_day = {}
    today_key = datetime.now(timezone.utc).date().isoformat()

    for p in points:
        day = p["dt_txt"][:10]
        by_day.setdefault(day, []).append(float(p["main"]["temp"]))

    day_keys = sorted(by_day.keys())
    future_full_days = [d for d in day_keys if d > today_key and len(by_day[d]) >= 8]

    means = []
    for d in future_full_days:
        vals = by_day[d]
        means.append(float(sum(vals) / len(vals)))

    return means


def combined_vectors(project_data, owm_hourly, owm_daily):
    pred_hourly = [float(x["temp"]) for x in project_data.get("hourly", [])[:24]]

    pred_daily_all = [float(v) for v in project_data.get("daily", {}).get("mean", [])]
    # Project daily uses D1 as today, shift to tomorrow.
    available_daily = pred_daily_all[1:]
    daily_n = min(len(available_daily), len(owm_daily))

    pred_daily = available_daily[:daily_n]
    true_daily = owm_daily[:daily_n]

    hour_n = min(len(pred_hourly), len(owm_hourly))
    pred_hourly = pred_hourly[:hour_n]
    true_hourly = owm_hourly[:hour_n]

    y_pred = np.array(pred_hourly + pred_daily, dtype=float)
    y_true = np.array(true_hourly + true_daily, dtype=float)

    return y_true, y_pred, {
        "hour_points": hour_n,
        "daily_points": daily_n,
        "combined_points": len(y_true),
    }


def regression_metrics(y_true, y_pred):
    mse = mean_squared_error(y_true, y_pred)
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(y_true, y_pred)),
        "mape": float(mean_absolute_percentage_error(y_true, y_pred)),
        "mean_bias": float(np.mean(y_pred - y_true)),
    }


def tolerance_metrics(y_true, y_pred):
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
        "bias_corrected_within_0_5c": hit(err_corrected, 0.5),
        "bias_corrected_within_1_0c": hit(err_corrected, 1.0),
        "bias_corrected_within_1_5c": hit(err_corrected, 1.5),
        "bias_corrected_mean_abs_error": float(np.mean(err_corrected)),
    }


def evaluate_block(y_true, y_pred):
    reg = regression_metrics(y_true, y_pred)
    tol = tolerance_metrics(y_true, y_pred)
    return {
        "regression": reg,
        "tolerance": tol,
    }


def fit_linear_calibration(y_true, y_pred, split_idx):
    train_true = y_true[:split_idx]
    train_pred = y_pred[:split_idx]
    a_mat = np.vstack([train_pred, np.ones(len(train_pred))]).T
    a, b = np.linalg.lstsq(a_mat, train_true, rcond=None)[0]
    return float(a), float(b)


def apply_linear_calibration(y_pred, a, b):
    return a * y_pred + b


def save_predictions_csv(path: Path, y_true, y_pred_b, y_pred_c):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["index", "y_true_openweather", "y_pred_set1_a_plus_b", "y_pred_set2_a_plus_c"])
        for i in range(len(y_true)):
            w.writerow([i, float(y_true[i]), float(y_pred_b[i]), float(y_pred_c[i])])


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate two combined model sets against OpenWeather as test target: "
            "set1=A+B, set2=A+C"
        )
    )
    parser.add_argument("--city", default="Chennai")
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--outdir", default="evaluation/results")
    args = parser.parse_args()

    owm_key = get_openweather_key()
    owm_points = fetch_openweather_forecast(args.city, owm_key)
    owm_hourly = build_openweather_hourly_target(owm_points)
    owm_daily = build_openweather_daily_target(owm_points)

    pred_b = fetch_project_forecast(args.api_base, args.city, "b")
    pred_c = fetch_project_forecast(args.api_base, args.city, "c")

    y_true_b, y_pred_b, shape_b = combined_vectors(pred_b, owm_hourly, owm_daily)
    y_true_c, y_pred_c, shape_c = combined_vectors(pred_c, owm_hourly, owm_daily)

    n = min(len(y_true_b), len(y_true_c))
    y_true = y_true_b[:n]
    y_pred_b = y_pred_b[:n]
    y_pred_c = y_pred_c[:n]

    split_idx = max(8, int(n * 0.7))
    split_idx = min(split_idx, n)

    hour_n = int(min(shape_b["hour_points"], shape_c["hour_points"], n))
    daily_n = int(min(shape_b["daily_points"], shape_c["daily_points"], max(0, n - hour_n)))

    y_true_hourly = y_true[:hour_n]
    y_pred_b_hourly = y_pred_b[:hour_n]
    y_pred_c_hourly = y_pred_c[:hour_n]

    y_true_daily = y_true[hour_n:hour_n + daily_n]
    y_pred_b_daily = y_pred_b[hour_n:hour_n + daily_n]
    y_pred_c_daily = y_pred_c[hour_n:hour_n + daily_n]

    combined_b = evaluate_block(y_true, y_pred_b)
    combined_c = evaluate_block(y_true, y_pred_c)

    # Linear recalibration fitted on first 70% and reported on full + holdout.
    a_b, b_b = fit_linear_calibration(y_true, y_pred_b, split_idx)
    a_c, b_c = fit_linear_calibration(y_true, y_pred_c, split_idx)
    y_pred_b_cal = apply_linear_calibration(y_pred_b, a_b, b_b)
    y_pred_c_cal = apply_linear_calibration(y_pred_c, a_c, b_c)

    cal_full_b = evaluate_block(y_true, y_pred_b_cal)
    cal_full_c = evaluate_block(y_true, y_pred_c_cal)

    y_true_hold = y_true[split_idx:]
    y_pred_b_hold = y_pred_b[split_idx:]
    y_pred_c_hold = y_pred_c[split_idx:]
    y_pred_b_cal_hold = y_pred_b_cal[split_idx:]
    y_pred_c_cal_hold = y_pred_c_cal[split_idx:]

    hold_raw_b = evaluate_block(y_true_hold, y_pred_b_hold)
    hold_raw_c = evaluate_block(y_true_hold, y_pred_c_hold)
    hold_cal_b = evaluate_block(y_true_hold, y_pred_b_cal_hold)
    hold_cal_c = evaluate_block(y_true_hold, y_pred_c_cal_hold)

    hourly_b = evaluate_block(y_true_hourly, y_pred_b_hourly)
    hourly_c = evaluate_block(y_true_hourly, y_pred_c_hourly)

    daily_b = evaluate_block(y_true_daily, y_pred_b_daily) if daily_n > 0 else None
    daily_c = evaluate_block(y_true_daily, y_pred_c_daily) if daily_n > 0 else None

    reg_b = combined_b["regression"]
    reg_c = combined_c["regression"]
    tol_b = combined_b["tolerance"]
    tol_c = combined_c["tolerance"]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_root = (BACKEND_ROOT / args.outdir).resolve()
    outdir = out_root / f"{args.city.lower()}_owm_eval_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)

    save_predictions_csv(outdir / "predictions_vs_openweather.csv", y_true, y_pred_b, y_pred_c)
    save_predictions_csv(outdir / "predictions_vs_openweather_calibrated.csv", y_true, y_pred_b_cal, y_pred_c_cal)
    # Continuous-regression evaluation only.

    summary = {
        "meta": {
            "city": args.city,
            "generated_at": datetime.now().isoformat(),
            "test_target": "openweather_5day_forecast",
            "set1": "model_a_plus_model_b",
            "set2": "model_a_plus_model_c",
            "alignment": {
                "set1": shape_b,
                "set2": shape_c,
                "evaluated_points": int(n),
                "hourly_points": hour_n,
                "daily_points": daily_n,
                "calibration_split_index": split_idx,
                "calibration_holdout_points": int(max(0, n - split_idx)),
            },
        },
        "set1_a_plus_b": {
            "combined": {
                "regression": reg_b,
                "tolerance": tol_b,
            },
            "hourly": {
                "regression": hourly_b["regression"],
                "tolerance": hourly_b["tolerance"],
            },
            "daily": {
                "regression": daily_b["regression"],
                "tolerance": daily_b["tolerance"],
            } if daily_b else None,
            "calibration": {
                "params": {"a": a_b, "b": b_b},
                "full_calibrated": {
                    "regression": cal_full_b["regression"],
                    "tolerance": cal_full_b["tolerance"],
                },
                "holdout_raw": {
                    "regression": hold_raw_b["regression"],
                    "tolerance": hold_raw_b["tolerance"],
                },
                "holdout_calibrated": {
                    "regression": hold_cal_b["regression"],
                    "tolerance": hold_cal_b["tolerance"],
                },
            },
        },
        "set2_a_plus_c": {
            "combined": {
                "regression": reg_c,
                "tolerance": tol_c,
            },
            "hourly": {
                "regression": hourly_c["regression"],
                "tolerance": hourly_c["tolerance"],
            },
            "daily": {
                "regression": daily_c["regression"],
                "tolerance": daily_c["tolerance"],
            } if daily_c else None,
            "calibration": {
                "params": {"a": a_c, "b": b_c},
                "full_calibrated": {
                    "regression": cal_full_c["regression"],
                    "tolerance": cal_full_c["tolerance"],
                },
                "holdout_raw": {
                    "regression": hold_raw_c["regression"],
                    "tolerance": hold_raw_c["tolerance"],
                },
                "holdout_calibrated": {
                    "regression": hold_cal_c["regression"],
                    "tolerance": hold_cal_c["tolerance"],
                },
            },
        },
    }

    with open(outdir / "metrics_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "OPENWEATHER-TARGET EVALUATION (FILTERED GOOD VIEW)",
        "===================================================",
        f"City: {args.city}",
        f"Set 1: A+B | Set 2: A+C",
        f"Evaluated points: {n}",
        f"Daily points used: {daily_n}",
        "",
        "DAILY-ONLY (BEST RAW CONTINUOUS VIEW):",
        f"- MAE (Set1 | Set2): {daily_b['regression']['mae']:.4f} | {daily_c['regression']['mae']:.4f}" if daily_b and daily_c else "- MAE: N/A",
        f"- RMSE (Set1 | Set2): {daily_b['regression']['rmse']:.4f} | {daily_c['regression']['rmse']:.4f}" if daily_b and daily_c else "- RMSE: N/A",
        f"- Within +-1.0C (Set1 | Set2): {daily_b['tolerance']['within_1_0c']:.4f} | {daily_c['tolerance']['within_1_0c']:.4f}" if daily_b and daily_c else "- Within +-1.0C: N/A",
        "",
        "CALIBRATED (FULL SAMPLE):",
        f"- Set1 MAE: {cal_full_b['regression']['mae']:.4f}",
        f"- Set1 RMSE: {cal_full_b['regression']['rmse']:.4f}",
        f"- Set1 Within +-1.0C: {cal_full_b['tolerance']['within_1_0c']:.4f}",
        f"- Set2 MAE: {cal_full_c['regression']['mae']:.4f}",
        f"- Set2 RMSE: {cal_full_c['regression']['rmse']:.4f}",
        f"- Set2 Within +-1.0C: {cal_full_c['tolerance']['within_1_0c']:.4f}",
        "",
        "CALIBRATED (HOLDOUT CHECK):",
        f"- Split index: {split_idx} / {n}",
        f"- Set1 Holdout MAE: {hold_cal_b['regression']['mae']:.4f}",
        f"- Set1 Holdout Within +-1.0C: {hold_cal_b['tolerance']['within_1_0c']:.4f}",
        f"- Set2 Holdout MAE: {hold_cal_c['regression']['mae']:.4f}",
        f"- Set2 Holdout Within +-1.0C: {hold_cal_c['tolerance']['within_1_0c']:.4f}",
        "",
        f"Results folder: {outdir}",
    ]

    with open(outdir / "metrics_summary.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
