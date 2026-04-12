"""
Test diurnal peak timing correction
Verifies that hourly forecasts now peak in afternoon (not morning)
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from app.db.database import SessionLocal
from app.models.weather_features import WeatherFeatures
from app.services.ml_predictor import predict_next_24_hours
from app.services.aggregation import get_hourly_climatology

def test_peak_timing(city="Chennai"):
    print(f"\n{'='*70}")
    print(f"DIURNAL PEAK TIMING VERIFICATION — {city}")
    print(f"{'='*70}\n")
    
    db = SessionLocal()
    
    # Get latest features
    latest = (
        db.query(WeatherFeatures)
        .filter(WeatherFeatures.city == city)
        .order_by(WeatherFeatures.recorded_at.desc())
        .first()
    )
    
    if not latest:
        print("No features found")
        return
    
    print(f"Starting from: {latest.recorded_at}")
    print(f"Current temp: {latest.temp:.1f}°C")
    print(f"Current hour: {latest.recorded_at.hour:02d}:00\n")
    
    # Get climatology for reference
    clim = get_hourly_climatology(city, db)
    hourly_clim = clim["hourly"]
    
    # Find climatological peak hour
    clim_peak_hour = max(hourly_clim.items(), key=lambda x: x[1])[0]
    clim_peak_temp = hourly_clim[clim_peak_hour]
    
    print(f"Climatological peak: {clim_peak_hour:02d}:00 ({clim_peak_temp:.1f}°C)")
    print(f"(This is the long-term average peak timing)\n")
    
    # Generate 24-hour forecast with correction
    forecast = predict_next_24_hours(city)
    
    # Analyze forecast
    current_hour = latest.recorded_at.hour
    forecast_hours = [(current_hour + h) % 24 for h in range(24)]
    
    # Find predicted peak
    peak_idx = np.argmax(forecast)
    peak_hour = forecast_hours[peak_idx]
    peak_temp = forecast[peak_idx]
    
    # Find predicted minimum
    min_idx = np.argmin(forecast)
    min_hour = forecast_hours[min_idx]
    min_temp = forecast[min_idx]
    
    print("="*70)
    print("FORECAST RESULTS")
    print("="*70 + "\n")
    
    print(f"Predicted peak:   {peak_hour:02d}:00 ({peak_temp:.1f}°C)")
    print(f"Predicted min:    {min_hour:02d}:00 ({min_temp:.1f}°C)")
    print(f"Amplitude:        {peak_temp - min_temp:.1f}°C\n")
    
    # Display hourly forecast
    print("Hour │ Temp  │ Note")
    print("─────┼───────┼─────────────────────")
    
    for i, temp in enumerate(forecast):
        h = forecast_hours[i]
        marker = ""
        if i == peak_idx:
            marker = "← PEAK"
        elif i == min_idx:
            marker = "← MIN"
        elif h in [clim_peak_hour, (clim_peak_hour+1)%24, (clim_peak_hour-1)%24]:
            marker = ""
        
        print(f" {h:02d}  │ {temp:5.1f}°C│ {marker}")
    
    # Assessment
    print(f"\n{'='*70}")
    print("ASSESSMENT")
    print(f"{'='*70}\n")
    
    # Check if peak is in afternoon (12-17)
    afternoon_peak = 12 <= peak_hour <= 17
    
    # Check if peak is close to climatology (within 3 hours)
    peak_timing_error = abs(peak_hour - clim_peak_hour)
    if peak_timing_error > 12:  # Handle wraparound
        peak_timing_error = 24 - peak_timing_error
    
    print(f"  Peak hour: {peak_hour:02d}:00")
    
    if afternoon_peak:
        print(f"  ✅ Peak occurs in afternoon (12-17h) — PHYSICALLY REALISTIC")
    else:
        print(f"  ⚠️  Peak at hour {peak_hour} (expected 12-17h)")
    
    print(f"\n  Climatology peak: {clim_peak_hour:02d}:00")
    print(f"  Timing difference: {peak_timing_error} hours")
    
    if peak_timing_error <= 2:
        print(f"  ✅ Peak timing matches climatology (±2h) — CORRECTION WORKING")
    elif peak_timing_error <= 4:
        print(f"  ⚠️  Slight deviation from climatology ({peak_timing_error}h)")
    else:
        print(f"  ❌ Large deviation from climatology ({peak_timing_error}h)")
    
    # Check for artifacts
    max_jump = max(abs(forecast[i+1] - forecast[i]) for i in range(len(forecast)-1))
    print(f"\n  Max hourly change: {max_jump:.2f}°C")
    
    if max_jump < 2.0:
        print(f"  ✅ No sharp discontinuities")
    else:
        print(f"  ⚠️  Large hourly jump detected")
    
    # Final verdict
    print(f"\n{'='*70}")
    
    if afternoon_peak and peak_timing_error <= 2 and max_jump < 2.0:
        print("✅ CORRECTION SUCCESSFUL")
        print("   - Peak timing is physically realistic")
        print("   - Matches climatological pattern")
        print("   - No artificial artifacts introduced")
    else:
        print("⚠️  REVIEW NEEDED")
        if not afternoon_peak:
            print("   - Peak still occurs too early")
        if peak_timing_error > 2:
            print("   - Significant deviation from climatology")
        if max_jump >= 2.0:
            print("   - Sharp temperature jumps detected")
    
    print(f"{'='*70}\n")
    
    db.close()

if __name__ == "__main__":
    test_peak_timing("Chennai")
