import os
from datetime import datetime
from math import pi, sin

import joblib
import numpy as np

from app.services.aggregation import get_daily_weather
from app.services.models.model_b import forecast_daily_model_b


MODEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "models")
)
MODEL_SUFFIX = "_model_c_et.joblib"
HISTORY_DAYS = 30


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _std(values):
    if not values:
        return 0.0
    arr = np.array(values, dtype=float)
    return float(arr.std())


def _slope(values):
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)
    return float(np.polyfit(x, y, 1)[0])


def _build_feature_vector(history_temps, forecast_start_date):
    """Builds the same feature vector used during model C training."""
    if len(history_temps) < HISTORY_DAYS:
        return None

    h = [float(v) for v in history_temps[-HISTORY_DAYS:]]

    last_7 = h[-7:]
    last_14 = h[-14:]
    last_30 = h[-30:]

    doy = forecast_start_date.timetuple().tm_yday

    feats = []
    feats.extend(h[-7:])
    feats.extend(
        [
            _mean(last_7),
            _std(last_7),
            min(last_7),
            max(last_7),
            _mean(last_14),
            _std(last_14),
            _mean(last_30),
            _std(last_30),
            _slope(last_7),
            _slope(last_14),
            _slope(last_30),
            sin(2 * pi * doy / 365.0),
            sin(2 * pi * (doy + 1) / 365.0),
        ]
    )
    return np.array(feats, dtype=float)


def _heuristic_fallback(city: str, db):
    """
    Legacy Model C fallback when trained artifacts are missing.
    """
    daily = get_daily_weather(city, db)
    temps = [float(r["avg_temp"]) for r in daily if r.get("avg_temp") is not None]

    if len(temps) < 14:
        return forecast_daily_model_b(city, db)

    long_window = temps[-60:] if len(temps) >= 60 else temps
    recent_window = temps[-14:]
    week_now = temps[-7:]
    week_prev = temps[-14:-7]

    long_mean = _mean(long_window)
    recent_mean = _mean(recent_window)
    drift = recent_mean - long_mean

    weekly_slope = 0.0
    if week_prev:
        weekly_slope = (_mean(week_now) - _mean(week_prev)) / 7.0

    amplitude = max(0.6, min(2.6, 0.45 * max(recent_window) - 0.45 * min(recent_window)))
    base = recent_mean + 0.30 * drift

    means = []
    for day in range(7):
        seasonal = amplitude * sin(2 * pi * day / 7)
        trend = weekly_slope * day
        means.append(round(base + seasonal + trend, 2))

    upper = [round(v + (2.0 + 0.1 * i), 2) for i, v in enumerate(means)]
    lower = [round(v - (2.0 + 0.1 * i), 2) for i, v in enumerate(means)]

    return {
        "mean": means,
        "upper": upper,
        "lower": lower,
    }


def forecast_daily_model_c(city: str, db):
    """
    Model C: Trained long-term model (ExtraTrees multi-output) with fallback.
    """
    model_path = os.path.join(MODEL_DIR, f"{city}{MODEL_SUFFIX}")

    try:
        artifact = joblib.load(model_path)

        daily = get_daily_weather(city, db)
        if len(daily) < HISTORY_DAYS:
            return _heuristic_fallback(city, db)

        temps = [float(r["avg_temp"]) for r in daily]
        latest_date = datetime.fromisoformat(daily[-1]["date"]).date()
        forecast_start = latest_date

        x = _build_feature_vector(temps, forecast_start)
        if x is None:
            return _heuristic_fallback(city, db)

        model = artifact["model"]
        pred = model.predict(x.reshape(1, -1))[0]
        means = [float(v) for v in pred[:7]]

        # Bias correction learned from validation split during training.
        calibration = artifact.get("calibration", {}) if isinstance(artifact, dict) else {}
        bias = calibration.get("bias_by_horizon") or []
        if len(bias) >= 7:
            means = [means[i] - float(bias[i]) for i in range(7)]

        # Keep Model C adaptive but softly anchored to stable climatology baseline.
        baseline_b = forecast_daily_model_b(city, db).get("mean", [])
        if len(baseline_b) >= 7:
            blend_weight_b = 0.60
            means = [
                (1.0 - blend_weight_b) * means[i] + blend_weight_b * float(baseline_b[i])
                for i in range(7)
            ]

        means = [round(v, 2) for v in means]

        # Build uncertainty band from recent observed variability.
        recent_std = _std(temps[-14:])
        spread = max(1.2, min(3.2, 1.25 * recent_std))
        upper = [round(v + spread, 2) for v in means]
        lower = [round(v - spread, 2) for v in means]

        return {
            "mean": means,
            "upper": upper,
            "lower": lower,
        }
    except Exception:
        return _heuristic_fallback(city, db)
