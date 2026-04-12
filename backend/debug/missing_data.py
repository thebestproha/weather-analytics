"""
Data validation: Missing data patterns
Guides safe imputation strategy
"""
import sys
sys.path.insert(0, "E:/prabanjan/weather x/weather-copy/backend")

from app.db.database import SessionLocal
from app.models.weather import Weather
import pandas as pd
from datetime import datetime, timedelta

def analyze_missing_data():
    db = SessionLocal()
    
    cities = db.query(Weather.city).distinct().all()
    
    print(f"\n{'='*60}")
    print("MISSING DATA ANALYSIS")
    print(f"{'='*60}\n")
    
    for (city,) in cities:
        print(f"\n{city}:")
        print("-" * 40)
        
        rows = (
            db.query(Weather.recorded_at)
            .filter(Weather.city == city)
            .order_by(Weather.recorded_at)
            .all()
        )
        
        if not rows:
            print("  No data")
            continue
        
        timestamps = [r[0] for r in rows]
        df = pd.DataFrame({'ts': timestamps})
        df['ts'] = pd.to_datetime(df['ts'])
        df = df.set_index('ts')
        
        start = df.index.min()
        end = df.index.max()
        
        print(f"  Period: {start.date()} to {end.date()}")
        print(f"  Records: {len(timestamps):,}")
        
        # Create complete hourly range
        full_range = pd.date_range(start=start.floor('h'), end=end.ceil('h'), freq='h')
        expected = len(full_range)
        actual = len(timestamps)
        missing = expected - actual
        
        print(f"  Expected: {expected:,} hours")
        print(f"  Missing: {missing:,} hours ({missing/expected*100:.1f}%)")
        
        if missing == 0:
            print("  ✅ Complete data - no gaps")
            continue
        
        # Analyze gap patterns
        df_full = pd.DataFrame(index=full_range)
        df_full['present'] = df_full.index.isin(df.index)
        
        # Find gaps
        gaps = []
        gap_start = None
        for idx, present in df_full['present'].items():
            if not present:
                if gap_start is None:
                    gap_start = idx
            else:
                if gap_start is not None:
                    gap_end = idx - timedelta(hours=1)
                    gap_hours = int((gap_end - gap_start).total_seconds() / 3600) + 1
                    gaps.append((gap_start, gap_end, gap_hours))
                    gap_start = None
        
        # Handle gap at end
        if gap_start is not None:
            gap_end = full_range[-1]
            gap_hours = int((gap_end - gap_start).total_seconds() / 3600) + 1
            gaps.append((gap_start, gap_end, gap_hours))
        
        # Categorize gaps
        small_gaps = [g for g in gaps if g[2] <= 3]
        medium_gaps = [g for g in gaps if 3 < g[2] <= 24]
        large_gaps = [g for g in gaps if 24 < g[2] <= 168]  # 1 week
        huge_gaps = [g for g in gaps if g[2] > 168]
        
        print(f"\n  Gap Analysis:")
        print(f"    1-3 hours:   {len(small_gaps):3d} gaps → INTERPOLATE")
        print(f"    4-24 hours:  {len(medium_gaps):3d} gaps → CONSIDER DROPPING")
        print(f"    1-7 days:    {len(large_gaps):3d} gaps → DROP PERIOD")
        print(f"    >7 days:     {len(huge_gaps):3d} gaps → DROP PERIOD")
        
        # Show largest gaps
        if gaps:
            gaps_sorted = sorted(gaps, key=lambda x: x[2], reverse=True)
            print(f"\n  Largest gaps (top 5):")
            for start, end, hours in gaps_sorted[:5]:
                days = hours / 24
                print(f"    {start.date()} to {end.date()}: {hours:,} hours ({days:.1f} days)")
    
    db.close()
    print("\n" + "="*60)
    print("\nIMPUTATION RULES:")
    print("  ✅ 1-3 hours missing  → Linear interpolation")
    print("  ⚠️  4-24 hours missing → Consider dropping day")
    print("  ❌ >1 day missing     → Drop entire period")
    print("  ❌ NEVER fabricate seasonal/diurnal patterns")
    print("="*60 + "\n")

if __name__ == "__main__":
    analyze_missing_data()
