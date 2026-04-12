"""
Data validation: Yearly and monthly counts
"""
import sys
sys.path.insert(0, "E:/prabanjan/weather x/weather-copy/backend")

from app.db.database import SessionLocal
from app.models.weather import Weather
from sqlalchemy import func, extract

def analyze_data():
    db = SessionLocal()
    
    # Total count
    total = db.query(Weather).count()
    print(f"\n{'='*60}")
    print(f"TOTAL RECORDS: {total:,}")
    print(f"{'='*60}\n")
    
    # By city
    print("BY CITY:")
    city_counts = (
        db.query(Weather.city, func.count(Weather.id))
        .group_by(Weather.city)
        .order_by(func.count(Weather.id).desc())
        .all()
    )
    for city, count in city_counts:
        print(f"  {city:20s} {count:8,} rows")
    
    # By source
    print("\nBY SOURCE:")
    source_counts = (
        db.query(Weather.source, func.count(Weather.id))
        .group_by(Weather.source)
        .all()
    )
    for source, count in source_counts:
        print(f"  {source:20s} {count:8,} rows")
    
    # Yearly breakdown (per city)
    print("\nYEARLY BREAKDOWN:")
    for city, _ in city_counts:
        print(f"\n  {city}:")
        yearly = (
            db.query(
                extract('year', Weather.recorded_at).label('year'),
                func.count(Weather.id)
            )
            .filter(Weather.city == city)
            .group_by('year')
            .order_by('year')
            .all()
        )
        for year, count in yearly:
            expected_hours = 8760 if int(year) % 4 != 0 else 8784  # leap year
            coverage = (count / expected_hours) * 100
            print(f"    {int(year)}: {count:6,} rows ({coverage:5.1f}% coverage)")
    
    # Monthly breakdown for latest year
    print("\nMONTHLY BREAKDOWN (2025):")
    for city, _ in city_counts:
        monthly = (
            db.query(
                extract('month', Weather.recorded_at).label('month'),
                func.count(Weather.id)
            )
            .filter(
                Weather.city == city,
                extract('year', Weather.recorded_at) == 2025
            )
            .group_by('month')
            .order_by('month')
            .all()
        )
        if monthly:
            print(f"\n  {city}:")
            month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            for month, count in monthly:
                print(f"    {month_names[int(month)]}: {count:4,} rows")
    
    db.close()
    print("\n" + "="*60)

if __name__ == "__main__":
    analyze_data()
