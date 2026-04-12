import os
import sys
from datetime import UTC, datetime
from math import pi, sin

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.multioutput import MultiOutputRegressor

from app.db.database import SessionLocal
from app.models.weather import Weather
from app.services.aggregation import get_daily_weather

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
MODEL_SUFFIX = "_model_c_et.joblib"
LOCK_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "PRODUCTION_LOCK_MODEL_C.txt")
)
HISTORY_DAYS = 30
HORIZON_DAYS = 7


def _mean(values):
    if not values:
        return 0.0
    return float(np.mean(np.array(values, dtype=float)))


def _std(values):
    if not values:
        return 0.0
    return float(np.std(np.array(values, dtype=float)))


def _slope(values):
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)
    return float(np.polyfit(x, y, 1)[0])


def _build_feature_vector(history_temps, forecast_start_date):
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


def _build_dataset(daily_rows):
    dates = [datetime.fromisoformat(r["date"]).date() for r in daily_rows]
    temps = [float(r["avg_temp"]) for r in daily_rows]

    x_data = []
    y_data = []

    for i in range(HISTORY_DAYS, len(temps) - HORIZON_DAYS + 1):
        history = temps[i - HISTORY_DAYS:i]
        target = temps[i:i + HORIZON_DAYS]

        x = _build_feature_vector(history, dates[i])
        if x is None:
            continue

        x_data.append(x)
        y_data.append(target)

    if not x_data:
        return None, None

    return np.array(x_data, dtype=float), np.array(y_data, dtype=float)


def train_model_c_all_cities():
    force_train = "--force" in sys.argv or os.getenv("MODEL_C_FORCE_TRAIN") == "1"
    if os.path.exists(LOCK_FILE) and not force_train:
        print("=" * 72)
        print("MODEL C TRAINING BLOCKED - PRODUCTION LOCK ACTIVE")
        print("=" * 72)
        print(f"Lock file: {LOCK_FILE}")
        print("Use --force or MODEL_C_FORCE_TRAIN=1 only after explicit approval.")
        return

    os.makedirs(MODEL_DIR, exist_ok=True)

    db = SessionLocal()
    cities = [r[0] for r in db.query(Weather.city).distinct().all()]

    print("=" * 72)
    print("MODEL C TRAINING - EXTRA TREES MULTI-OUTPUT (7-DAY DAILY FORECAST)")
    print("=" * 72)

    for city in cities:
        print(f"\nCity: {city}")
        print("-" * 72)

        daily = get_daily_weather(city, db)
        if len(daily) < 120:
            print(f"  Skipped: insufficient daily history ({len(daily)} days)")
            continue

        x_all, y_all = _build_dataset(daily)
        if x_all is None or len(x_all) < 80:
            print("  Skipped: not enough supervised samples after feature build")
            continue

        split = int(len(x_all) * 0.8)
        x_train, x_val = x_all[:split], x_all[split:]
        y_train, y_val = y_all[:split], y_all[split:]

        base = ExtraTreesRegressor(
            n_estimators=500,
            max_depth=16,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        model = MultiOutputRegressor(base)
        model.fit(x_train, y_train)

        y_pred = model.predict(x_val)
        mae_all = mean_absolute_error(y_val, y_pred)
        mae_d1 = mean_absolute_error(y_val[:, 0], y_pred[:, 0])
        mae_d7 = mean_absolute_error(y_val[:, 6], y_pred[:, 6])
        bias_by_horizon = np.mean(y_pred - y_val, axis=0)

        print(f"  Samples: train={len(x_train)}, val={len(x_val)}")
        print(f"  MAE overall: {mae_all:.3f} C")
        print(f"  MAE day-1:   {mae_d1:.3f} C")
        print(f"  MAE day-7:   {mae_d7:.3f} C")
        print(f"  Mean bias D1..D7: {[round(float(v), 3) for v in bias_by_horizon]}")

        artifact = {
            "model": model,
            "history_days": HISTORY_DAYS,
            "horizon_days": HORIZON_DAYS,
            "trained_at": datetime.now(UTC).isoformat(),
            "metrics": {
                "mae_overall": float(mae_all),
                "mae_day_1": float(mae_d1),
                "mae_day_7": float(mae_d7),
            },
            "calibration": {
                "bias_by_horizon": [float(v) for v in bias_by_horizon],
            },
        }

        path = os.path.join(MODEL_DIR, f"{city}{MODEL_SUFFIX}")
        joblib.dump(artifact, path)
        print(f"  Saved: {path}")

    db.close()

    print("\n" + "=" * 72)
    print("MODEL C TRAINING COMPLETE")
    print("=" * 72)


if __name__ == "__main__":
    train_model_c_all_cities()
