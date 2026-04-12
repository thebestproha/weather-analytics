"""
Diagnose Model A diurnal learning
- Feature importance
- Predicted vs actual diurnal curves
- Peak timing validation
"""
import sys
sys.path.insert(0, "E:/prabanjan/weather x/weather-copy/backend")

import joblib
import numpy as np
import pandas as pd
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

def diagnose_diurnal(city="Chennai"):
    print(f"\n{'='*70}")
    print(f"DIURNAL LEARNING DIAGNOSTICS — {city}")
    print(f"{'='*70}\n")
    
    # Load model
    model = joblib.load(f"backend/app/models/{city}_gbm.joblib")
    
    # Feature importance
    print("Feature Importance (top 10):")
    importances = model.feature_importances_
    feature_imp = sorted(zip(FEATURES, importances), key=lambda x: x[1], reverse=True)
    for feat, imp in feature_imp[:10]:
        print(f"  {feat:20s} {imp:.4f} {'█' * int(imp * 100)}")
    
    # Load validation data
    db = SessionLocal()
    rows = (
        db.query(WeatherFeatures)
        .filter(WeatherFeatures.city == city)
        .order_by(WeatherFeatures.recorded_at)
        .all()
    )
    
    # Time-aware split (same as training)
    split_idx = int(len(rows) * 0.8)
    val_rows = rows[split_idx:]
    
    # Extract validation features
    X_val = []
    y_val = []
    hours = []
    
    for r in val_rows:
        vals = [getattr(r, f) for f in FEATURES]
        if any(v is None for v in vals):
            continue
        X_val.append(vals)
        y_val.append(r.temp)
        hours.append(r.recorded_at.hour)
    
    X_val = np.array(X_val)
    y_val = np.array(y_val)
    hours = np.array(hours)
    
    # Predict
    y_pred = model.predict(X_val)
    
    # Compute hour-of-day statistics
    print(f"\n{'='*70}")
    print("DIURNAL CURVE VALIDATION")
    print(f"{'='*70}\n")
    
    hourly_stats = []
    for h in range(24):
        mask = hours == h
        if mask.sum() > 0:
            actual_mean = y_val[mask].mean()
            pred_mean = y_pred[mask].mean()
            hourly_stats.append({
                'hour': h,
                'actual': actual_mean,
                'predicted': pred_mean,
                'error': pred_mean - actual_mean
            })
    
    df_hourly = pd.DataFrame(hourly_stats)
    
    # Find peaks
    actual_peak_hour = df_hourly.loc[df_hourly['actual'].idxmax(), 'hour']
    pred_peak_hour = df_hourly.loc[df_hourly['predicted'].idxmax(), 'hour']
    
    actual_min_hour = df_hourly.loc[df_hourly['actual'].idxmin(), 'hour']
    pred_min_hour = df_hourly.loc[df_hourly['predicted'].idxmin(), 'hour']
    
    print(f"Temperature Peak (hottest hour):")
    print(f"  Actual:    {int(actual_peak_hour):02d}:00 ({df_hourly.loc[df_hourly['hour']==actual_peak_hour, 'actual'].values[0]:.1f}°C)")
    print(f"  Predicted: {int(pred_peak_hour):02d}:00 ({df_hourly.loc[df_hourly['hour']==pred_peak_hour, 'predicted'].values[0]:.1f}°C)")
    print(f"  Timing error: {int(pred_peak_hour - actual_peak_hour)} hours")
    
    print(f"\nTemperature Minimum (coolest hour):")
    print(f"  Actual:    {int(actual_min_hour):02d}:00 ({df_hourly.loc[df_hourly['hour']==actual_min_hour, 'actual'].values[0]:.1f}°C)")
    print(f"  Predicted: {int(pred_min_hour):02d}:00 ({df_hourly.loc[df_hourly['hour']==pred_min_hour, 'predicted'].values[0]:.1f}°C)")
    print(f"  Timing error: {int(pred_min_hour - actual_min_hour)} hours")
    
    # Diurnal amplitude
    actual_amp = df_hourly['actual'].max() - df_hourly['actual'].min()
    pred_amp = df_hourly['predicted'].max() - df_hourly['predicted'].min()
    
    print(f"\nDiurnal Amplitude:")
    print(f"  Actual:    {actual_amp:.2f}°C")
    print(f"  Predicted: {pred_amp:.2f}°C")
    print(f"  Difference: {pred_amp - actual_amp:+.2f}°C")
    
    # Visual comparison
    print(f"\n{'='*70}")
    print("HOURLY TEMPERATURE CURVE")
    print(f"{'='*70}\n")
    print("Hour │ Actual  │ Predicted │ Error")
    print("─────┼─────────┼───────────┼────────")
    
    for _, row in df_hourly.iterrows():
        h = int(row['hour'])
        actual = row['actual']
        pred = row['predicted']
        error = row['error']
        marker = "✓" if abs(error) < 0.2 else ("⚠" if abs(error) < 0.5 else "✗")
        print(f" {h:02d}  │ {actual:6.2f}°C│ {pred:6.2f}°C │ {error:+.2f}°C {marker}")
    
    # Assessment
    print(f"\n{'='*70}")
    print("ASSESSMENT")
    print(f"{'='*70}\n")
    
    peak_timing_ok = abs(pred_peak_hour - actual_peak_hour) <= 2
    min_timing_ok = abs(pred_min_hour - actual_min_hour) <= 2
    amplitude_ok = abs(pred_amp - actual_amp) < 1.0
    
    print(f"  Peak timing: {'✅ CORRECT' if peak_timing_ok else '❌ SHIFTED'}")
    print(f"  Min timing:  {'✅ CORRECT' if min_timing_ok else '❌ SHIFTED'}")
    print(f"  Amplitude:   {'✅ REALISTIC' if amplitude_ok else '❌ DISTORTED'}")
    
    if peak_timing_ok and min_timing_ok and amplitude_ok:
        print(f"\n✅ Model learns realistic diurnal curves")
    else:
        print(f"\n⚠️  Diurnal learning needs investigation")
        if not peak_timing_ok:
            print(f"    → Peak shifted by {int(pred_peak_hour - actual_peak_hour)} hours")
            print(f"    → Check: sin_hour/cos_hour importance, hourly data balance")
    
    db.close()
    print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    diagnose_diurnal("Chennai")
