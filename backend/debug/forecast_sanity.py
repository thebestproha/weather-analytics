"""
Generate sample forecasts and check for:
- Sharp discontinuities
- Unrealistic peak timings
- Artificial convergence
"""
import sys
sys.path.insert(0, "E:/prabanjan/weather x/weather-copy/backend")

import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from math import sin, cos, pi
from app.db.database import SessionLocal
from app.models.weather_features import WeatherFeatures

FEATURES = [
    "temp_lag_1","temp_lag_3","temp_lag_6","temp_lag_24","temp_lag_72","temp_lag_168",
    "temp_mean_72h","temp_mean_168h",
    "temp_trend_72h","temp_trend_168h",
    "delta_1h","delta_24h",
    "roll_mean_24h","roll_std_24h",
    "sin_hour","cos_hour","sin_doy"
]

def forecast_24h(city="Chennai"):
    """Generate 24-hour forecast using Model A"""
    print(f"\n{'='*70}")
    print(f"24-HOUR FORECAST SANITY CHECK — {city}")
    print(f"{'='*70}\n")
    
    # Load model
    model = joblib.load(f"backend/app/models/{city}_gbm.joblib")
    
    # Get latest features
    db = SessionLocal()
    latest = (
        db.query(WeatherFeatures)
        .filter(WeatherFeatures.city == city)
        .order_by(WeatherFeatures.recorded_at.desc())
        .first()
    )
    
    if not latest:
        print("No features found")
        return
    
    print(f"Latest data: {latest.recorded_at}")
    print(f"Current temp: {latest.temp:.1f}°C\n")
    
    # Extract current features
    current_features = [getattr(latest, f) for f in FEATURES]
    
    # Predict next 24 hours
    forecasts = []
    state = current_features.copy()
    current_time = latest.recorded_at
    
    for h in range(24):
        # Predict
        pred_temp = model.predict([state])[0]
        
        next_time = current_time + timedelta(hours=h+1)
        forecasts.append({
            'hour': (current_time.hour + h + 1) % 24,
            'timestamp': next_time,
            'temp': pred_temp
        })
        
        # Update state with prediction for next iteration
        # (This is a simplified rollout - production would update all lags)
        state[0] = pred_temp  # temp_lag_1
        state[13] = sin(2*pi*((current_time.hour + h + 1) % 24)/24)  # sin_hour
        state[14] = cos(2*pi*((current_time.hour + h + 1) % 24)/24)  # cos_hour
    
    df = pd.DataFrame(forecasts)
    
    # Check for discontinuities
    df['delta'] = df['temp'].diff()
    max_jump = df['delta'].abs().max()
    
    print("Hour │ Temp  │ Change")
    print("─────┼───────┼────────")
    for _, row in df.iterrows():
        h = int(row['hour'])
        temp = row['temp']
        delta = row['delta']
        
        if pd.notna(delta):
            flag = "⚠" if abs(delta) > 2.0 else ""
            print(f" {h:02d}  │ {temp:5.1f}°C│ {delta:+6.2f}°C {flag}")
        else:
            print(f" {h:02d}  │ {temp:5.1f}°C│   ---")
    
    # Sanity checks
    print(f"\n{'='*70}")
    print("SANITY CHECKS")
    print(f"{'='*70}\n")
    
    peak_hour = df.loc[df['temp'].idxmax(), 'hour']
    min_hour = df.loc[df['temp'].idxmin(), 'hour']
    
    print(f"  Max temp: {df['temp'].max():.1f}°C at hour {int(peak_hour):02d}:00")
    print(f"  Min temp: {df['temp'].min():.1f}°C at hour {int(min_hour):02d}:00")
    print(f"  Max hourly change: {max_jump:.2f}°C")
    
    # Check for issues
    issues = []
    if max_jump > 3.0:
        issues.append(f"❌ Sharp discontinuity ({max_jump:.2f}°C)")
    else:
        print(f"  ✅ No sharp discontinuities (max {max_jump:.2f}°C)")
    
    if 0 <= peak_hour <= 5:
        issues.append(f"❌ Early morning peak (hour {int(peak_hour)})")
    else:
        print(f"  ✅ Realistic peak timing (hour {int(peak_hour)})")
    
    if df['temp'].max() > 45 or df['temp'].min() < 15:
        issues.append("❌ Unrealistic temperature range")
    else:
        print(f"  ✅ Realistic temperature range")
    
    if issues:
        print(f"\n⚠️  Issues detected:")
        for issue in issues:
            print(f"    {issue}")
    else:
        print(f"\n✅ All sanity checks passed")
    
    db.close()
    print("\n" + "="*70 + "\n")

def forecast_7d_baseline(city="Chennai"):
    """Model B: 7-day seasonal baseline"""
    print(f"{'='*70}")
    print(f"7-DAY SEASONAL BASELINE — Model B")
    print(f"{'='*70}\n")
    
    db = SessionLocal()
    
    # Get daily aggregates (Model B uses daily data)
    from app.models.weather import Weather
    from sqlalchemy import func, extract
    
    # Get monthly climatology
    monthly_means = (
        db.query(
            extract('month', Weather.recorded_at).label('month'),
            func.avg(Weather.temperature).label('avg_temp')
        )
        .filter(Weather.city == city)
        .group_by('month')
        .all()
    )
    
    month_clim = {int(m): float(temp) for m, temp in monthly_means}
    
    # Get current month
    from datetime import datetime
    current_month = datetime.now().month
    
    print(f"Current month: {current_month}")
    print(f"Seasonal baseline: {month_clim.get(current_month, 28.0):.1f}°C\n")
    
    # Simple 7-day forecast (climatology-based)
    print("Day │ Temp (baseline)")
    print("────┼─────────────────")
    
    for day in range(1, 8):
        future_month = ((current_month - 1 + day // 30) % 12) + 1
        baseline = month_clim.get(future_month, 28.0)
        print(f"  {day} │ {baseline:5.1f}°C")
    
    print(f"\n✅ Model B: Simple seasonal baseline (no ML needed)")
    
    db.close()
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    forecast_24h("Chennai")
    forecast_7d_baseline("Chennai")
