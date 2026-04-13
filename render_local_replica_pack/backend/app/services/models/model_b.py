from datetime import datetime, timedelta

from app.services.aggregation import get_daily_weather
from app.services.ml_predictor import predict_next_7_days


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _std(values):
    if not values:
        return 0.0
    m = _mean(values)
    var = sum((v - m) ** 2 for v in values) / len(values)
    return var ** 0.5


def _circular_doy_distance(a: int, b: int) -> int:
    diff = abs(a - b)
    return min(diff, 365 - diff)


def _seasonal_targets(rows, forecast_start, horizon=7):
    dated = []
    for row in rows:
        try:
            d = datetime.fromisoformat(row["date"]).date()
            t = float(row["avg_temp"])
            dated.append((d, t))
        except Exception:
            continue

    if not dated:
        return []

    month_buckets = {}
    for d, t in dated:
        month_buckets.setdefault(d.month, []).append(t)

    all_mean = _mean([t for _, t in dated])
    targets = []

    for i in range(horizon):
        target_date = forecast_start + timedelta(days=i)
        target_doy = target_date.timetuple().tm_yday

        near = [
            t
            for d, t in dated
            if _circular_doy_distance(d.timetuple().tm_yday, target_doy) <= 25
        ]

        if len(near) >= 10:
            targets.append(_mean(near))
            continue

        month_vals = month_buckets.get(target_date.month, [])
        if month_vals:
            targets.append(_mean(month_vals))
        else:
            targets.append(all_mean)

    return targets


def _build_bands(means, recent_values):
    recent_std = _std(recent_values[-14:]) if recent_values else 1.5
    spread = max(1.5, min(3.0, 1.1 * recent_std))
    upper = [round(v + spread, 2) for v in means]
    lower = [round(v - spread, 2) for v in means]
    return upper, lower


def forecast_daily_model_b(city: str, db=None):
    """
    Model B: Climatology-oriented long-term baseline.
    """
    if db is None:
        return predict_next_7_days(city)

    rows = get_daily_weather(city, db)
    if len(rows) < 45:
        return predict_next_7_days(city)

    temps = [float(r["avg_temp"]) for r in rows if r.get("avg_temp") is not None]
    if len(temps) < 14:
        return predict_next_7_days(city)

    latest_date = datetime.fromisoformat(rows[-1]["date"]).date()
    seasonal = _seasonal_targets(rows, latest_date, horizon=7)
    if len(seasonal) < 7:
        return predict_next_7_days(city)

    # Keep recent anomaly influence, but decay by horizon so seasonality dominates later days.
    recent_mean = _mean(temps[-7:])
    anomaly = recent_mean - seasonal[0]

    means = []
    for i in range(7):
        anomaly_weight = max(0.15, 0.45 - 0.05 * i)
        value = seasonal[i] + anomaly * anomaly_weight
        means.append(round(value, 2))

    upper, lower = _build_bands(means, temps)

    return {
        "mean": means,
        "upper": upper,
        "lower": lower,
    }
