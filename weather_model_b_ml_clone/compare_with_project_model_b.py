import os
import sqlite3
from math import sin, pi

from predict_model_b_ml_clone import predict_daily

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DB_PATH = os.path.join(PROJECT_ROOT, "weather.db")

CITY_PROFILE = {
    "Delhi": {"amp": 5.5, "trend": 0.03},
    "Ahmedabad": {"amp": 5.0, "trend": 0.03},
    "Jaipur": {"amp": 5.2, "trend": 0.03},
    "Chennai": {"amp": 2.5, "trend": 0.02},
    "Mumbai": {"amp": 2.2, "trend": 0.02},
    "Kochi": {"amp": 2.0, "trend": 0.02},
    "Trivandrum": {"amp": 1.8, "trend": 0.02},
    "Bengaluru": {"amp": 2.3, "trend": 0.02},
    "Hyderabad": {"amp": 3.0, "trend": 0.025},
    "Kolkata": {"amp": 3.2, "trend": 0.025},
    "Pune": {"amp": 2.6, "trend": 0.02},
}


def model_b_formula(base, amp, trend):
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


def latest_base_for_city(conn, city):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT roll_mean_24h
        FROM weather_features
        WHERE city = ?
        ORDER BY recorded_at DESC
        LIMIT 1
        """,
        (city,),
    )
    row = cur.fetchone()
    return None if row is None else float(row[0])


def main():
    conn = sqlite3.connect(DB_PATH)
    cities = sorted(CITY_PROFILE.keys())

    print("Model B ML Clone vs current Model B formula")
    print("=" * 72)

    total_abs = 0.0
    total_n = 0

    for city in cities:
        base = latest_base_for_city(conn, city)
        if base is None:
            print(f"{city:12s}: skipped (no weather_features)")
            continue

        amp = CITY_PROFILE[city]["amp"]
        trend = CITY_PROFILE[city]["trend"]

        target = model_b_formula(base, amp, trend)
        pred = predict_daily(base, amp, trend)["mean"]

        diffs = [round(p - t, 4) for p, t in zip(pred, target)]
        mae = sum(abs(d) for d in diffs) / len(diffs)

        total_abs += sum(abs(d) for d in diffs)
        total_n += len(diffs)

        print(f"{city:12s}: MAE={mae:.4f} | diffs={diffs}")

    if total_n:
        print("-" * 72)
        print(f"Global MAE: {total_abs / total_n:.4f}")

    conn.close()


if __name__ == "__main__":
    main()
