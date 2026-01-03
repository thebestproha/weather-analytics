from datetime import datetime
from backend.app.services.meteostat_bulk_ingest import bulk_ingest_city

def ingest_city_all_years(city, lat, lon, start_year, end_year):
    for year in range(start_year, end_year + 1):
        print(f"[BULK] {city} {year}")
        bulk_ingest_city(
            city,
            lat,
            lon,
            datetime(year, 1, 1),
            datetime(year, 12, 31)
        )
