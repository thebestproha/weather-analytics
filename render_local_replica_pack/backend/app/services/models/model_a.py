from datetime import datetime

from app.services.ml_predictor import predict_next_24_hours


def forecast_hourly_model_a(city: str, current_temp: float, current_hour: int | None = None):
    """
    Model A: GBM short-term forecast with physics-aware correction.
    Returns 24 hourly points in API-ready structure.
    """
    hour = datetime.now().hour if current_hour is None else int(current_hour) % 24
    hourly_temps = predict_next_24_hours(city, live_temp=current_temp, current_hour=hour)

    if not hourly_temps:
        return []

    return [
        {
            "hour": f"{(hour + i) % 24:02d}:00",
            "temp": temp,
        }
        for i, temp in enumerate(hourly_temps)
    ]
