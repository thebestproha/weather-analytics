from backend.app.constants.city_coords import CITY_COORDS
from backend.app.services.era5_downloader import download_city_month
from backend.app.services.era5_ingest import ingest_era5_file
from pathlib import Path

BASE=Path("data/era5/raw")

def run_city_year(city,year,months):
    lat,lon=CITY_COORDS[city]
    city_dir=BASE/city
    city_dir.mkdir(parents=True,exist_ok=True)

    for m in months:
        print(f"=== {city} {year}-{m:02d} ===")
        instant=city_dir/f"{city}_{year}_{m:02d}_instant.nc"
        accum=city_dir/f"{city}_{year}_{m:02d}_accum.nc"

        if not instant.exists():
            download_city_month(city,lat,lon,year,m,"instant",instant)
        if not accum.exists():
            download_city_month(city,lat,lon,year,m,"accum",accum)

        ingest_era5_file(str(instant),city)
        ingest_era5_file(str(accum),city)
