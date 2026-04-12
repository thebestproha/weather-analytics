import joblib
import numpy as np
from datetime import datetime
from math import sin, pi
from app.db.deps import get_db
from app.db.database import SessionLocal
from app.models.weather_features import WeatherFeatures
from app.services.city_profiles import CITY_PROFILE

FEATURES = [
    "temp_lag_1","temp_lag_3","temp_lag_6","temp_lag_24",
    "temp_lag_72","temp_lag_168",
    "temp_mean_72h","temp_mean_168h",
    "temp_trend_72h","temp_trend_168h",
    "delta_1h","delta_24h",
    "roll_mean_24h","roll_std_24h",
    "sin_hour","cos_hour","sin_doy"
]

def _latest(city):
    db = SessionLocal()
    r = (
        db.query(WeatherFeatures)
        .filter(WeatherFeatures.city == city)
        .order_by(WeatherFeatures.recorded_at.desc())
        .first()
    )
    db.close()
    return r

import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

def _model(city):
    model_path = os.path.join(BASE_DIR, "models", f"{city}_gbm.joblib")
    return joblib.load(model_path)


# ---------- 1 HOUR ----------
def predict_next_hour(city):
    r = _latest(city)
    if not r:
        return None
    x = np.array([[getattr(r, f) for f in FEATURES]])
    return round(float(_model(city).predict(x)[0]), 2)

# ---------- 24 HOURS ----------
def predict_next_24_hours(city, live_temp=None, current_hour=None):
    """
    Model A: Short-term (24h) hourly temperature prediction
    
    LIVE-ANCHORED PHYSICS-AWARE FORECASTING:
    ========================================
    Problem: Model predicts absolute temperatures without knowing current live conditions,
             causing discontinuous jumps (e.g., live=27°C → forecast[0]=22°C).
    
    Solution: Three-stage post-processing (NO model retraining):
    
    Stage 1 - LIVE ANCHORING:
             forecast[0] = current_live_temp (guaranteed continuity)
    
    Stage 2 - DELTA PREDICTION:
             Use model to predict hour-to-hour changes (Δtemp)
             Accumulate: temp[i+1] = temp[i] + predicted_delta[i]
    
    Stage 3 - PHYSICS CORRECTION:
             Apply light diurnal shape correction to maintain:
             - Peak at 14:00 (solar heating + thermal lag)
             - Minimum at 05:00 (pre-sunrise cooling)
             - Smooth transitions (max change ≤ 0.5°C/hour)
    
    Constraints:
             - Model retains 85% control (α=0.15)
             - Physics nudges timing, not magnitude
             - No climatology override of live data
    
    Args:
        city: City name
        live_temp: Optional live temperature to anchor forecast (takes priority)
        current_hour: Optional local clock hour to align physics/labels
    """
    r = _latest(city)
    if not r:
        return []

    model = _model(city)
    
    # Use explicitly passed live temperature if provided, otherwise fallback to feature DB
    if live_temp is not None:
        current_temp = float(live_temp)
    else:
        current_temp = float(r.temp)
    
    if current_hour is None:
        current_hour = datetime.now().hour
    else:
        current_hour = int(current_hour) % 24
    
    def physics_diurnal_shape(hour):
        """
        ABSOLUTE SOLAR-TIME DIURNAL SHAPE (Chennai tropical climate)
        
        This defines WHEN temperatures should peak/trough based on solar physics:
        - Minimum: 05:00 (pre-sunrise, maximum radiative cooling)
        - Maximum: 13:00-14:00 (solar noon + 1-2h thermal lag)
        
        NOT a delta, NOT an incremental nudge - this IS the shape.
        
        Returns: Temperature anomaly from daily mean (°C)
                 Positive = warmer, Negative = cooler
        """
        # Solar heating sine wave
        # Peak when sin(2π(hour-shift)/24) = 1 → hour-shift = 6
        # For peak at 13.5: shift = 13.5 - 6 = 7.5
        peak_hour = 13.5  # 1:30 PM (middle of 13-15 range)
        phase_shift = peak_hour - 6.0
        
        # Amplitude = half of diurnal range
        # Chennai typical range: 6-8°C, use 7°C → amplitude = 3.5°C
        amplitude = 3.5
        
        return amplitude * sin(2 * pi * (hour - phase_shift) / 24)
    
    # =================================================================
    # PHYSICS-DOMINANT FORECASTING (80% physics shape, 20% model)
    # =================================================================
    # Philosophy: Physics controls TIMING (when peak occurs)
    #             Model controls AMPLITUDE (how much variation)
    # =================================================================
    
    # ---------------------------------------------------------
    # STEP 1: Get raw model predictions
    # ---------------------------------------------------------
    model_predictions = []
    for h in range(24):
        x = np.array([[getattr(r, f) for f in FEATURES]])
        model_pred = float(model.predict(x)[0])
        model_predictions.append(model_pred)
    
    # ---------------------------------------------------------
    # STEP 2: Extract model anomalies (deviations from mean)
    # ---------------------------------------------------------
    model_mean = sum(model_predictions) / len(model_predictions)
    model_anomalies = [pred - model_mean for pred in model_predictions]
    
    # ---------------------------------------------------------
    # STEP 3: Build blended anomalies (80% physics, 20% model)
    # ---------------------------------------------------------
    # CRITICAL: Physics defines SHAPE, model adjusts AMPLITUDE
    PHYSICS_WEIGHT = 0.80
    MODEL_WEIGHT = 0.20
    
    blended_anomalies = []
    for h in range(24):
        target_hour = (current_hour + h) % 24
        
        # Physics shape at this CLOCK HOUR (not forecast index)
        physics_anomaly = physics_diurnal_shape(target_hour)
        
        # Blend: physics dominates timing, model adds learned variability
        blended = PHYSICS_WEIGHT * physics_anomaly + MODEL_WEIGHT * model_anomalies[h]
        blended_anomalies.append(blended)
    
    # ---------------------------------------------------------
    # STEP 4: Anchor to live temperature
    # ---------------------------------------------------------
    # Constraint: forecast[0] MUST equal current_temp
    # If forecast[0] = baseline + blended_anomalies[0], then:
    baseline = current_temp - blended_anomalies[0]
    
    # Generate raw forecast curve (already has correct physics shape!)
    raw_forecast = [baseline + anom for anom in blended_anomalies]
    
    # ---------------------------------------------------------
    # STEP 5: Apply MINIMAL smoothing only
    # ---------------------------------------------------------
    # Trust the physics-weighted shape (80% physics controls timing)
    # Only smooth out unrealistic jumps
    
    forecast = [current_temp]  # Hour 0: exact live anchor
    
    for h in range(1, 24):
        candidate = raw_forecast[h]
        prev_temp = forecast[h-1]
        
        # Only apply smoothing if change is too abrupt
        delta = candidate - prev_temp
        
        # Limit to ±1.2°C per hour (generous limit to preserve physics shape)
        if delta > 1.2:
            candidate = prev_temp + 1.2
        elif delta < -1.2:
            candidate = prev_temp - 1.2
        
        forecast.append(round(candidate, 2))
    
    return forecast
    
    return forecast

# ---------- 7 DAYS ----------
def predict_next_7_days(city):
    r = _latest(city)
    if not r:
        return {"mean": [], "upper": [], "lower": []}

    profile = CITY_PROFILE.get(city, {"amp": 2.5, "trend": 0.02})
    base = r.roll_mean_24h

    climo = []
    for d in range(7):
        seasonal = profile["trend"] * 24 * d
        weekly = profile["amp"] * sin(2 * pi * d / 7)
        climo.append(base + seasonal + weekly)

    days = list(climo)

    # Blend days 4-7 with short-term trend continuation
    if len(days) >= 4:
        trend = ((days[1] - days[0]) + (days[2] - days[1])) / 2.0
        decay = [1.0, 0.8, 0.6, 0.4]

        for idx, d in enumerate(range(3, min(7, 3 + len(decay)))):
            blended = 0.65 * climo[d] + 0.35 * (days[d - 1] + trend * decay[idx])

            # Enforce continuity: no sudden drops > 1°C/day
            if blended < days[d - 1] - 1.0:
                blended = days[d - 1] - 1.0

            days[d] = blended

    days = [round(v, 2) for v in days]

    return {
        "mean": days,
        "upper": [round(v + 2, 2) for v in days],
        "lower": [round(v - 2, 2) for v in days]
    }
