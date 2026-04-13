import joblib
import os
import numpy as np
from app.db.database import SessionLocal
from app.models.weather_features import WeatherFeatures
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

FEATURES = [
    "temp_lag_1","temp_lag_3","temp_lag_6","temp_lag_24","temp_lag_72","temp_lag_168",
    "temp_mean_72h","temp_mean_168h",
    "temp_trend_72h","temp_trend_168h",
    "delta_1h","delta_24h",
    "roll_mean_24h","roll_std_24h",
    "sin_hour","cos_hour","sin_doy"
]

MODEL_DIR = "backend/app/models"
os.makedirs(MODEL_DIR,exist_ok=True)

def train_all():
    """
    Train GBM models with time-aware split and validation diagnostics
    """
    db = SessionLocal()
    cities = [r[0] for r in db.query(WeatherFeatures.city).distinct()]
    
    print(f"\n{'='*70}")
    print("MODEL A TRAINING — SHORT-TERM HOURLY PREDICTION (GBM)")
    print(f"{'='*70}\n")

    for city in cities:
        print(f"City: {city}")
        print("-" * 70)
        
        rows = (
            db.query(WeatherFeatures)
            .filter(WeatherFeatures.city == city)
            .order_by(WeatherFeatures.recorded_at)  # TIME-ORDERED
            .all()
        )

        # Extract features and target
        X = []
        y = []
        timestamps = []
        hours = []
        
        for r in rows:
            vals = [getattr(r, f) for f in FEATURES]
            if any(v is None for v in vals):
                continue
            X.append(vals)
            y.append(r.temp)
            timestamps.append(r.recorded_at)
            hours.append(r.recorded_at.hour)

        if len(X) < 500:
            print(f"  ⚠️  Insufficient data ({len(X)} rows), skipping\n")
            continue

        X = np.array(X)
        y = np.array(y)
        hours = np.array(hours)
        
        # TIME-AWARE SPLIT (80/20, no shuffling)
        split_idx = int(len(X) * 0.8)
        
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        hours_val = hours[split_idx:]
        
        train_period = f"{timestamps[0].date()} to {timestamps[split_idx-1].date()}"
        val_period = f"{timestamps[split_idx].date()} to {timestamps[-1].date()}"
        
        print(f"  Train period: {train_period}")
        print(f"  Val period:   {val_period}")
        print(f"  Train samples: {len(X_train):,}")
        print(f"  Val samples:   {len(X_val):,}")

        # Train GBM
        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42
        )
        model.fit(X_train, y_train)

        # Validation metrics
        y_pred = model.predict(X_val)
        
        mae_overall = mean_absolute_error(y_val, y_pred)
        print(f"\n  Overall MAE: {mae_overall:.3f}°C")
        
        # MAE by hour-of-day (diurnal diagnostic)
        print(f"\n  MAE by hour-of-day:")
        mae_by_hour = []
        for h in range(24):
            mask = hours_val == h
            if mask.sum() > 0:
                mae_h = mean_absolute_error(y_val[mask], y_pred[mask])
                mae_by_hour.append((h, mae_h))
        
        # Group into time periods for readability
        print("    Night (00-05):  ", end="")
        night_mae = np.mean([mae for h, mae in mae_by_hour if 0 <= h <= 5])
        print(f"{night_mae:.3f}°C")
        
        print("    Morning (06-11):", end="")
        morning_mae = np.mean([mae for h, mae in mae_by_hour if 6 <= h <= 11])
        print(f"{morning_mae:.3f}°C")
        
        print("    Afternoon (12-17):", end="")
        afternoon_mae = np.mean([mae for h, mae in mae_by_hour if 12 <= h <= 17])
        print(f"{afternoon_mae:.3f}°C")
        
        print("    Evening (18-23):", end="")
        evening_mae = np.mean([mae for h, mae in mae_by_hour if 18 <= h <= 23])
        print(f"{evening_mae:.3f}°C")

        # Save model
        model_path = f"{MODEL_DIR}/{city}_gbm.joblib"
        joblib.dump(model, model_path)
        print(f"\n  ✅ Model saved: {model_path}\n")

    db.close()
    
    print("="*70)
    print("TRAINING COMPLETE")
    print("="*70 + "\n")

if __name__=="__main__":
    train_all()
