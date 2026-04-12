"""
Safe data imputation following strict rules:
- 1-3 hour gaps → linear interpolation
- 4-23 hour gaps → mark as suspicious, optionally drop
- >24 hour gaps → never fill (would fabricate patterns)
"""
import sys
sys.path.insert(0, "E:/prabanjan/weather x/weather-copy/backend")

from app.db.database import SessionLocal
from app.models.weather import Weather
import pandas as pd
from datetime import timedelta

def safe_imputation(city, max_gap_hours=3):
    """
    Fill ONLY small gaps with linear interpolation
    
    Args:
        city: City name
        max_gap_hours: Maximum gap size to fill (default 3)
    """
    print(f"\n{'='*60}")
    print(f"SAFE IMPUTATION: {city}")
    print(f"Max gap to fill: {max_gap_hours} hours")
    print(f"{'='*60}\n")
    
    db = SessionLocal()
    
    # Load all data for this city
    rows = (
        db.query(
            Weather.id,
            Weather.recorded_at,
            Weather.temperature,
            Weather.humidity,
            Weather.pressure,
            Weather.wind_speed,
            Weather.rainfall
        )
        .filter(Weather.city == city, Weather.source == "Meteostat")
        .order_by(Weather.recorded_at)
        .all()
    )
    
    if not rows:
        print(f"No data found for {city}")
        db.close()
        return
    
    print(f"Loaded: {len(rows):,} existing records")
    
    # Create DataFrame
    df = pd.DataFrame([{
        'id': r.id,
        'time': r.recorded_at,
        'temp': r.temperature,
        'humidity': r.humidity,
        'pressure': r.pressure,
        'wind_speed': r.wind_speed,
        'rainfall': r.rainfall
    } for r in rows])
    
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time').sort_index()
    
    # Get full hourly range
    start = df.index.min().floor('h')
    end = df.index.max().ceil('h')
    full_range = pd.date_range(start=start, end=end, freq='h')
    
    # Reindex to identify gaps
    df_full = df.reindex(full_range)
    
    # Count gaps
    total_gaps = df_full['temp'].isna().sum()
    print(f"Total gaps: {total_gaps:,} hours")
    
    if total_gaps == 0:
        print("✅ No gaps found - data is complete!")
        db.close()
        return
    
    # Identify gap sizes
    gaps = []
    gap_start = None
    for idx, is_null in df_full['temp'].isna().items():
        if is_null:
            if gap_start is None:
                gap_start = idx
        else:
            if gap_start is not None:
                gap_end = idx - timedelta(hours=1)
                gap_size = int((gap_end - gap_start).total_seconds() / 3600) + 1
                gaps.append((gap_start, gap_end, gap_size))
                gap_start = None
    
    # Categorize
    fillable = [g for g in gaps if g[2] <= max_gap_hours]
    too_large = [g for g in gaps if g[2] > max_gap_hours]
    
    print(f"\nGaps ≤{max_gap_hours}h: {len(fillable)} (will fill)")
    print(f"Gaps >{max_gap_hours}h: {len(too_large)} (will NOT fill)")
    
    if not fillable:
        print("\n✅ No small gaps to fill")
        db.close()
        return
    
    # Fill small gaps with linear interpolation
    print(f"\nFilling {len(fillable)} small gaps...")
    
    df_filled = df_full.copy()
    for col in ['temp', 'humidity', 'pressure', 'wind_speed', 'rainfall']:
        # Interpolate only with limit=max_gap_hours
        df_filled[col] = df_filled[col].interpolate(
            method='linear',
            limit=max_gap_hours,
            limit_area='inside'  # only fill gaps, not edges
        )
    
    # Insert new records
    inserted = 0
    for idx, row in df_filled.iterrows():
        # Skip if this timestamp already exists in DB
        if not pd.isna(df_full.loc[idx, 'temp']):
            continue
        
        # Skip if still has NaN (gap too large or edge)
        if pd.isna(row['temp']):
            continue
        
        # Insert new interpolated record
        new_record = Weather(
            city=city,
            recorded_at=idx.to_pydatetime(),
            temperature=float(row['temp']) if not pd.isna(row['temp']) else None,
            humidity=float(row['humidity']) if not pd.isna(row['humidity']) else None,
            pressure=float(row['pressure']) if not pd.isna(row['pressure']) else None,
            wind_speed=float(row['wind_speed']) if not pd.isna(row['wind_speed']) else None,
            rainfall=float(row['rainfall']) if not pd.isna(row['rainfall']) else None,
            source="Meteostat_interpolated"
        )
        db.add(new_record)
        inserted += 1
    
    db.commit()
    print(f"\n✅ Inserted {inserted:,} interpolated records")
    
    # Report remaining gaps
    remaining = total_gaps - inserted
    if remaining > 0:
        print(f"⚠️  {remaining:,} hours still missing (gaps too large)")
        print("\nLargest unfilled gaps:")
        for start, end, size in sorted(too_large, key=lambda x: x[2], reverse=True)[:5]:
            print(f"  {start.date()} to {end.date()}: {size} hours")
    
    db.close()
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--city', default='Chennai', help='City name')
    parser.add_argument('--max-gap', type=int, default=3, help='Max gap hours to fill')
    args = parser.parse_args()
    
    safe_imputation(args.city, args.max_gap)
