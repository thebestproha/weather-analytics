import os
import numpy as np
import xarray as xr
from datetime import datetime, timezone

from backend.app.models.weather import Weather


def ingest_era5_files(folder_path: str, city: str, db):
    print(f"Ingesting ERA5 directory: {folder_path} for {city}")

    instant_files = []
    accum_files = []

    for f in os.listdir(folder_path):
        if f.endswith("_instant.nc"):
            instant_files.append(os.path.join(folder_path, f))
        elif f.endswith("_accum.nc"):
            accum_files.append(os.path.join(folder_path, f))

    instant_files.sort()
    accum_files.sort()

    if not instant_files or not accum_files:
        raise RuntimeError("ERA5 instant or accum files missing")

    for instant_nc, accum_nc in zip(instant_files, accum_files):
        print(f"Opening: {instant_nc}")
        print(f"Opening: {accum_nc}")

        ds_i = xr.open_dataset(instant_nc)
        ds_a = xr.open_dataset(accum_nc)

        times = ds_i["valid_time"].values

        for idx in range(len(times)):
            recorded_at = datetime.fromtimestamp(
                times[idx].astype("datetime64[s]").astype(int),
                tz=timezone.utc
            )

            temp = (
                ds_i["t2m"]
                .isel(valid_time=idx)
                .mean(dim=["latitude", "longitude"])
                .values
            ) - 273.15

            dew = (
                ds_i["d2m"]
                .isel(valid_time=idx)
                .mean(dim=["latitude", "longitude"])
                .values
            ) - 273.15

            u10 = (
                ds_i["u10"]
                .isel(valid_time=idx)
                .mean(dim=["latitude", "longitude"])
                .values
            )

            v10 = (
                ds_i["v10"]
                .isel(valid_time=idx)
                .mean(dim=["latitude", "longitude"])
                .values
            )

            wind_speed = float(np.sqrt(u10 ** 2 + v10 ** 2))

            pressure = (
                ds_i["sp"]
                .isel(valid_time=idx)
                .mean(dim=["latitude", "longitude"])
                .values
            ) / 100.0

            rain = (
                ds_a["tp"]
                .isel(valid_time=idx)
                .mean(dim=["latitude", "longitude"])
                .values
            ) * 1000.0

            weather = Weather(
                city=city,
                temperature=float(temp),
                humidity=None,  # ERA5 does not give RH directly
                pressure=float(pressure),
                wind_speed=wind_speed,
                rainfall=float(rain),
                recorded_at=recorded_at,
                source="ERA5"
            )

            db.add(weather)

        db.commit()

        ds_i.close()
        ds_a.close()

    print(f"ERA5 ingestion completed for {city}")
