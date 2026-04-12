from app.services.models.model_b import forecast_daily_model_b
from app.services.models.model_c import forecast_daily_model_c


LONG_TERM_MODELS = {
    "b": {
        "name": "Model B (Climatology)",
        "forecast": forecast_daily_model_b,
    },
    "c": {
        "name": "Model C (Adaptive Trend)",
        "forecast": forecast_daily_model_c,
    },
}


def list_long_term_models():
    return {
        key: {"name": value["name"]}
        for key, value in LONG_TERM_MODELS.items()
    }


def get_long_term_model(model_id: str):
    key = (model_id or "b").strip().lower()
    return LONG_TERM_MODELS.get(key)
