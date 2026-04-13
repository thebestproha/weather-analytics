from datetime import datetime
from app.services.meteostat_bulk_ingest import bulk_ingest_city
from app.constants.city_coords import CITY_COORDS

def ingest_city_all_years(city, lat, lon, start_year, end_year):
    """Ingest hourly Meteostat data for a city across multiple years"""
    for year in range(start_year, end_year + 1):
        print(f"[BULK] {city} {year}")
        bulk_ingest_city(
            city,
            lat,
            lon,
            datetime(year, 1, 1),
            datetime(year, 12, 31)
        )

if __name__ == "__main__":
    print("[METEOSTAT] Starting bulk ingestion")
    print("[METEOSTAT] Target: Recent 3 years hourly data")
    
    # Start with Chennai (2023-2025)
    city = "Chennai"
    lat, lon = CITY_COORDS[city]
    
    ingest_city_all_years(
        city=city,
        lat=lat,
        lon=lon,
        start_year=2023,
        end_year=2025
    )
    
    print(f"[METEOSTAT] {city} ingestion complete")
