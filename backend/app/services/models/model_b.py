from app.services.ml_predictor import predict_next_7_days


def forecast_daily_model_b(city: str, db=None):
    """
    Model B: Climatology-oriented long-term baseline.
    """
    return predict_next_7_days(city)
