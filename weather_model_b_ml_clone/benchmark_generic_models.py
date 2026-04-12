import numpy as np
from math import sin, pi
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.linear_model import Ridge, MultiTaskElasticNet
from sklearn.multioutput import MultiOutputRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import train_test_split


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


def make_dataset(n_samples=80000, seed=42):
    rng = np.random.default_rng(seed)
    base = rng.uniform(18.0, 40.0, size=n_samples)
    amp = rng.uniform(1.5, 6.0, size=n_samples)
    trend = rng.uniform(0.015, 0.035, size=n_samples)

    X = np.column_stack([base, amp, trend])
    y = np.array([target_formula(b, a, t) for b, a, t in X], dtype=float)
    return train_test_split(X, y, test_size=0.2, random_state=42)


def evaluate(name, model, x_train, x_test, y_train, y_test):
    model.fit(x_train, y_train)
    pred = model.predict(x_test)
    overall = mean_absolute_error(y_test, pred)
    per_day = [mean_absolute_error(y_test[:, i], pred[:, i]) for i in range(7)]
    return {
        "name": name,
        "overall_mae": float(overall),
        "per_day_mae": [float(v) for v in per_day],
    }


def main():
    x_train, x_test, y_train, y_test = make_dataset()

    models = [
        (
            "RandomForest MultiOutput",
            RandomForestRegressor(
                n_estimators=500,
                random_state=42,
                n_jobs=-1,
            ),
        ),
        (
            "ExtraTrees MultiOutput",
            ExtraTreesRegressor(
                n_estimators=500,
                random_state=42,
                n_jobs=-1,
            ),
        ),
        (
            "Ridge MultiOutput",
            MultiOutputRegressor(Ridge(alpha=1.0)),
        ),
        (
            "MultiTaskElasticNet",
            MultiTaskElasticNet(alpha=0.001, l1_ratio=0.2, random_state=42, max_iter=5000),
        ),
        (
            "MLPRegressor MultiOutput",
            MLPRegressor(
                hidden_layer_sizes=(128, 128),
                activation="relu",
                solver="adam",
                random_state=42,
                max_iter=1200,
                early_stopping=True,
            ),
        ),
    ]

    results = []
    for name, model in models:
        print(f"Training: {name}")
        r = evaluate(name, model, x_train, x_test, y_train, y_test)
        results.append(r)
        print(f"  Overall MAE: {r['overall_mae']:.4f}")

    results.sort(key=lambda r: r["overall_mae"])

    print("\nRanked by MAE (lower is better)")
    print("=" * 72)
    for idx, r in enumerate(results, start=1):
        print(f"{idx:2d}. {r['name']:26s} | MAE={r['overall_mae']:.4f} | per_day={[round(v,4) for v in r['per_day_mae']]}")


if __name__ == "__main__":
    main()
