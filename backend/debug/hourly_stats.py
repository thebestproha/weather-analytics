"""
Data validation: Hourly distribution (0-23)
Critical for diurnal cycle modeling
"""
import sys
sys.path.insert(0, "E:/prabanjan/weather x/weather-copy/backend")

from app.db.database import SessionLocal
from app.models.weather import Weather
from sqlalchemy import func, extract

def analyze_hourly_distribution():
    db = SessionLocal()
    
    cities = db.query(Weather.city).distinct().all()
    
    print(f"\n{'='*60}")
    print("HOURLY DISTRIBUTION (0-23)")
    print("Why this matters: Imbalanced hours break diurnal curves")
    print(f"{'='*60}\n")
    
    for (city,) in cities:
        print(f"{city}:")
        
        hourly = (
            db.query(
                extract('hour', Weather.recorded_at).label('hour'),
                func.count(Weather.id)
            )
            .filter(Weather.city == city)
            .group_by('hour')
            .order_by('hour')
            .all()
        )
        
        if not hourly:
            print("  No data\n")
            continue
        
        # Calculate statistics
        counts = [count for _, count in hourly]
        avg_count = sum(counts) / len(counts)
        min_count = min(counts)
        max_count = max(counts)
        
        print(f"  Average: {avg_count:,.0f} | Min: {min_count:,} | Max: {max_count:,}")
        print(f"  Balance: {(min_count/avg_count*100):5.1f}% min, {(max_count/avg_count*100):5.1f}% max")
        
        # Visual bar chart
        print("  Distribution:")
        for hour, count in hourly:
            bar_length = int((count / max_count) * 40)
            bar = '█' * bar_length
            print(f"    {int(hour):02d}:00 │{bar} {count:,}")
        
        # Check for missing hours
        hours_present = set(int(h) for h, _ in hourly)
        missing_hours = set(range(24)) - hours_present
        if missing_hours:
            print(f"  ⚠️  MISSING HOURS: {sorted(missing_hours)}")
        
        # Check imbalance
        if max_count > avg_count * 1.5:
            print(f"  ⚠️  IMBALANCED: Peak hour has {max_count/avg_count:.1f}x average")
        
        print()
    
    db.close()
    print("="*60)
    print("\nIMPORTANCE:")
    print("- Diurnal models expect ~equal samples per hour")
    print("- Imbalance shifts predicted peak times")
    print("- Fix by ensuring even ingestion, not smoothing")
    print("="*60 + "\n")

if __name__ == "__main__":
    analyze_hourly_distribution()
