from backend.app.services.meteostat_bulk_runner import ingest_city_all_years
from backend.app.constants.city_coords import CITY_COORDS

START_YEAR = 2019
END_YEAR = 2025

def ingest_all_cities():
    for city, (lat, lon) in CITY_COORDS.items():
        print(f"\n=== STARTING {city} ===")
        ingest_city_all_years(city, lat, lon, START_YEAR, END_YEAR)
        print(f"=== COMPLETED {city} ===\n")
