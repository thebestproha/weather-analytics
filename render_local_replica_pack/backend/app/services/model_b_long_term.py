"""
Legacy compatibility wrapper.
Model B implementation now lives in app.services.models.model_b.
"""

from app.services.models.model_b import forecast_daily_model_b


def get_seasonal_baseline(city: str, db) -> dict:
    """
    Returns Model B daily forecast as compatibility output.
    """
    return forecast_daily_model_b(city, db)
