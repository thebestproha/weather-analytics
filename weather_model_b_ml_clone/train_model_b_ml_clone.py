import joblib
import numpy as np
from math import sin, pi
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split

MODEL_NAME = "Model B-ML Mimic (MultiOutput GBR)"
MODEL_FILE = "model_b_ml_mimic.joblib"


def target_formula(base, amp, trend):
    climo = []
    for d in range(7):
        seasonal = trend * 24 * d
        weekly = amp * sin(2 * pi * d / 7)
        climo.append(base + seasonal + weekly)

    days = list(climo)
    trend_est = ((days[1] - days[0]) + (days[2] - days[1])) / 2.0
    decay = [1.0, 0.8, 0.6, 0.4]

    for idx, d in enumerate(range(3, 7)):
        blended = 0.65 * climo[d] + 0.35 * (days[d - 1] + trend_est * decay[idx])
        if blended < days[d - 1] - 1.0:
            blended = days[d - 1] - 1.0
        days[d] = blended

    return [round(v, 2) for v in days]


def make_dataset(n_samples=50000, seed=42):
    rng = np.random.default_rng(seed)

    base = rng.uniform(18.0, 40.0, size=n_samples)
    amp = rng.uniform(1.5, 6.0, size=n_samples)
    trend = rng.uniform(0.015, 0.035, size=n_samples)

    X = np.column_stack([base, amp, trend])
    y = np.array([target_formula(b, a, t) for b, a, t in X], dtype=float)
    return X, y


def main():
    X, y = make_dataset()
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = MultiOutputRegressor(
        GradientBoostingRegressor(
            n_estimators=250,
            learning_rate=0.05,
            max_depth=4,
            random_state=42,
        )
    )

    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    overall_mae = mean_absolute_error(y_test, pred)
    per_day_mae = [mean_absolute_error(y_test[:, i], pred[:, i]) for i in range(7)]

    joblib.dump({"name": MODEL_NAME, "model": model}, MODEL_FILE)

    print(f"Saved: {MODEL_FILE}")
    print(f"Model: {MODEL_NAME}")
    print(f"Overall MAE: {overall_mae:.4f} C")
    print("Per-day MAE:", [round(v, 4) for v in per_day_mae])


if __name__ == "__main__":
    main()
