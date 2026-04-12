"""
Final gap filling using hourly climatology
For remaining small gaps that weren't caught by linear interpolation
"""
import sys
sys.path.insert(0, "E:/prabanjan/weather x/weather-copy/backend")

from app.db.database import SessionLocal
from app.models.weather import Weather
import pandas as pd
import numpy as np

def climatology_fill(city):
    """
    Fill remaining gaps using hour-of-day climatology
    Preserves diurnal curve shape
    """
    print(f"\n{'='*60}")
    print(f"CLIMATOLOGY-BASED GAP FILLING: {city}")
    print(f"{'='*60}\n")
    
    db = SessionLocal()
    
    # Load all data
    rows = (
        db.query(
            Weather.recorded_at,
            Weather.temperature,
            Weather.humidity,
            Weather.pressure,
            Weather.wind_speed,
            Weather.rainfall
        )
        .filter(Weather.city == city)
        .order_by(Weather.recorded_at)
        .all()
    )
    
    print(f"Loaded: {len(rows):,} records")
    
    # Create DataFrame
    df = pd.DataFrame([{
        'time': r.recorded_at,
        'temp': r.temperature,
        'humidity': r.humidity,
        'pressure': r.pressure,
        'wind_speed': r.wind_speed,
        'rainfall': r.rainfall
    } for r in rows])
    
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time').sort_index()
    
    # Calculate hourly climatology (mean by hour-of-day)
    df['hour'] = df.index.hour
    hourly_clim = df.groupby('hour').mean()
    
    print("\nHourly climatology calculated:")
    print(f"  Temperature range: {hourly_clim['temp'].min():.1f}°C to {hourly_clim['temp'].max():.1f}°C")
    
    # Get full hourly range
    start = df.index.min().floor('h')
    end = df.index.max().ceil('h')
    full_range = pd.date_range(start=start, end=end, freq='h')
    
    # Reindex
    df_full = df.reindex(full_range)
    
    # Count gaps
    gaps_before = df_full['temp'].isna().sum()
    print(f"\nGaps before fill: {gaps_before}")
    
    if gaps_before == 0:
        print("✅ No gaps to fill")
        db.close()
        return
    
    # Fill using climatology
    filled_count = 0
    for idx, row in df_full.iterrows():
        if pd.isna(row['temp']):
            hour = idx.hour
            clim = hourly_clim.loc[hour]
            
            # Insert climatology-based record
            new_record = Weather(
                city=city,
                recorded_at=idx.to_pydatetime(),
                temperature=float(clim['temp']),
                humidity=float(clim['humidity']) if not pd.isna(clim['humidity']) else None,
                pressure=float(clim['pressure']) if not pd.isna(clim['pressure']) else None,
                wind_speed=float(clim['wind_speed']) if not pd.isna(clim['wind_speed']) else None,
                rainfall=0.0,  # Conservative for missing rainfall
                source="Meteostat_climatology"
            )
            db.add(new_record)
            filled_count += 1
    
    db.commit()
    print(f"✅ Filled {filled_count} gaps using hourly climatology")
    
    # Final statistics
    total = db.query(Weather).filter(Weather.city == city).count()
    expected = len(full_range)
    print(f"\nFinal state:")
    print(f"  Total records: {total:,}")
    print(f"  Expected: {expected:,}")
    print(f"  Coverage: {total/expected*100:.2f}%")
    
    db.close()
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    climatology_fill("Chennai")
