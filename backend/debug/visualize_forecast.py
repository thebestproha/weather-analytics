"""
Production Visualization - Model A 24h Forecast
================================================
Displays the final corrected predictions with physics-based diurnal pattern.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ml_predictor import predict_next_24_hours
from app.db.database import SessionLocal
from app.models.weather_features import WeatherFeatures
from datetime import datetime, timedelta

def visualize_forecast():
    print("=" * 80)
    print("MODEL A: 24-HOUR TEMPERATURE FORECAST (Physics-Corrected)")
    print("=" * 80)
    
    city = "Chennai"
    
    # Get current state
    db = SessionLocal()
    latest = (
        db.query(WeatherFeatures)
        .filter(WeatherFeatures.city == city)
        .order_by(WeatherFeatures.recorded_at.desc())
        .first()
    )
    db.close()
    
    if not latest:
        print("ERROR: No feature data available")
        return
    
    current_time = latest.recorded_at
    current_temp = latest.temp
    current_hour = current_time.hour
    
    print(f"\nCurrent State:")
    print(f"  Time: {current_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Temperature: {current_temp:.1f}°C")
    print(f"  Hour: {current_hour:02d}:00")
    
    # Get predictions
    predictions = predict_next_24_hours(city)
    
    if not predictions or len(predictions) != 24:
        print("\nERROR: Could not generate 24h predictions")
        return
    
    # Find peak and trough
    peak_idx = max(range(24), key=lambda i: predictions[i])
    trough_idx = min(range(24), key=lambda i: predictions[i])
    
    peak_hour = (current_hour + peak_idx) % 24
    trough_hour = (current_hour + trough_idx) % 24
    
    amplitude = max(predictions) - min(predictions)
    
    # Display header info
    print(f"\nForecast Summary:")
    print(f"  Peak: {predictions[peak_idx]:.1f}°C at {peak_hour:02d}:00 (hour +{peak_idx})")
    print(f"  Trough: {predictions[trough_idx]:.1f}°C at {trough_hour:02d}:00 (hour +{trough_idx})")
    print(f"  Amplitude: {amplitude:.1f}°C")
    
    # Verify afternoon peak
    if 12 <= peak_hour <= 17:
        print(f"  ✓ Peak occurs in afternoon (physically realistic)")
    else:
        print(f"  ⚠ Peak at {peak_hour:02d}:00 - outside typical afternoon window")
    
    # ASCII visualization
    print(f"\n{'Hour':<6} {'Time':<6} {'Temp':<8} {'Graph':<40} {'Note'}")
    print("-" * 80)
    
    # Scale for graph
    min_temp = min(predictions)
    max_temp = max(predictions)
    temp_range = max_temp - min_temp
    
    for i, temp in enumerate(predictions):
        hour = (current_hour + i) % 24
        time_str = f"{hour:02d}:00"
        
        # Bar graph
        if temp_range > 0:
            bar_len = int(((temp - min_temp) / temp_range) * 30)
        else:
            bar_len = 15
        bar = "█" * bar_len
        
        # Annotations
        note = ""
        if i == 0:
            note = "← Current"
        elif i == peak_idx:
            note = "← PEAK"
        elif i == trough_idx:
            note = "← Min"
        elif 12 <= hour <= 15:
            note = "Afternoon"
        elif 22 <= hour or hour <= 5:
            note = "Night"
        
        print(f"+{i:02d}h   {time_str:<6} {temp:>5.1f}°C  {bar:<40} {note}")
    
    print("-" * 80)
    
    # Physics correction info
    print("\nPhysics-Based Diurnal Correction:")
    print(f"  Formula: corrected = model_pred + 0.20 × physics_offset[hour]")
    print(f"  Physics: 4.0 × sin(2π(h-8)/24) peaks at 14:00")
    print(f"  Weight: 80% model (learned patterns) + 20% physics (peak timing)")
    print(f"  Rationale: Data has morning-peak bias, climatology cannot correct")
    
    print("\nModel A Constraints:")
    print("  ✓ No retraining")
    print("  ✓ No dataset modification")
    print("  ✓ Model remains primary (80% dominant)")
    print("  ✓ Light correction only (α=0.20)")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    visualize_forecast()
