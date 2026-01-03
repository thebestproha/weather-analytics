from datetime import datetime
from meteostat import Point, Stations, Hourly
from backend.app.models.weather import Weather
from backend.app.db.database import SessionLocal
import pandas as pd

def _clean(v):
    if pd.isna(v):
        return None
    return float(v)

def bulk_ingest_city(city, lat, lon, start, end):
    print(f"[Meteostat] Ingesting {city} from {start.date()} to {end.date()}")

    point = Point(lat, lon)

    stations = Stations().nearby(lat, lon).fetch(1)
    if stations.empty:
        print(f"[Meteostat] No station found for {city}")
        return

    station_id = stations.index[0]
    print(f"[Meteostat] Using station {station_id}")

    data = Hourly(station_id, start, end).fetch()
    if data.empty:
        print(f"[Meteostat] No data returned for {city}")
        return

    db = SessionLocal()
    inserted = 0

    for ts, row in data.iterrows():
        exists = db.query(Weather).filter(
            Weather.city == city,
            Weather.recorded_at == ts
        ).first()
        if exists:
            continue

        w = Weather(
            city=city,
            temperature=_clean(row.get("temp")),
            humidity=_clean(row.get("rhum")),
            pressure=_clean(row.get("pres")),
            wind_speed=_clean(row.get("wspd")),
            rainfall=_clean(row.get("prcp")),
            recorded_at=ts,
            source="Meteostat"
        )
        db.add(w)
        inserted += 1

    db.commit()
    db.close()

    print(f"[Meteostat] Inserted {inserted} rows for {city}")
