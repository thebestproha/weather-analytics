def generate_hourly_forecast(
    current_temp: float,
    start_hour: int,
    climatology: dict,
    daily_mean: float
):
    hourly_climo = climatology["hourly"]
    daily_min = climatology["daily_min"]
    daily_max = climatology["daily_max"]

    forecast = []

    for i in range(24):
        hour = (start_hour + i) % 24
        base = hourly_climo.get(hour, daily_mean)

        # anchor strongly to now, fade smoothly
        w = max(0.0, 1.0 - i / 8.0)
        temp = w * current_temp + (1 - w) * base
        forecast.append(temp)

    # physical smoothing (no sharp spikes)
    smooth = [forecast[0]]
    for i in range(1, 24):
        smooth.append(0.75 * smooth[i - 1] + 0.25 * forecast[i])

    return [
        round(min(max(t, daily_min - 0.5), daily_max + 0.5), 2)
        for t in smooth
    ]
