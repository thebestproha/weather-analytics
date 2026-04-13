import requests
import os

WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY", "").strip()

def get_true_current_temp(city: str) -> float:
    if not WEATHERAPI_KEY:
        raise RuntimeError("WEATHERAPI_KEY is not set")

    url = (
        "https://api.weatherapi.com/v1/current.json"
        f"?key={WEATHERAPI_KEY}&q={city}&aqi=no"
    )

    r = requests.get(url, timeout=8)
    data = r.json()

    return float(data["current"]["temp_c"])
