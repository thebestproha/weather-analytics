import requests

TOMORROW_API_KEY = "KQpO7kQ5rPCrV64fR3NQ9PnbCGb8iOx1"


def get_tomorrow_features(city: str):
    url = (
        "https://api.tomorrow.io/v4/weather/realtime"
        f"?location={city}&apikey={TOMORROW_API_KEY}"
    )

    r = requests.get(url, timeout=10)
    data = r.json()["data"]["values"]

    return {
        "rain_probability": data.get("precipitationProbability"),
        "cloud_cover": data.get("cloudCover"),
        "feels_like": data.get("temperatureApparent"),
        "wind_gust": data.get("windGust"),
        "weather_code": data.get("weatherCode"),
    }