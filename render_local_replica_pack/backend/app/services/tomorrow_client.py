import requests

# 🔴 HARD-CODED API KEY (allowed for your case)
TOMORROW_API_KEY = "KQpO7kQ5rPCrV64fR3NQ9PnbCGb8iOx1"

def fetch_tomorrow_extras(lat: float, lon: float):
    url = "https://api.tomorrow.io/v4/weather/realtime"
    params = {
        "location": f"{lat},{lon}",
        "apikey": TOMORROW_API_KEY,
        "units": "metric"
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()

    values = r.json()["data"]["values"]

    return {
        "feels_like": values.get("temperatureApparent"),
        "cloud": values.get("cloudCover"),
        "rain": values.get("precipitationProbability"),
        "wind": values.get("windSpeed")
    }
