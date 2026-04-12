"""
Legacy compatibility wrapper.
Model A implementation now lives in app.services.models.model_a.
"""

from app.services.ml_predictor import predict_next_hour, predict_next_24_hours


def predict_short_term(city: str, current_temp: float | None = None, current_hour: int | None = None) -> dict:
    """
    Legacy helper retained for backward compatibility.
    """
    return {
        "next_1h": predict_next_hour(city),
        "next_24h": predict_next_24_hours(city, live_temp=current_temp, current_hour=current_hour),
    }
