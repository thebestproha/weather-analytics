import joblib
import os
from backend.app.db.database import SessionLocal
from backend.app.models.weather_features import WeatherFeatures
from sklearn.ensemble import GradientBoostingRegressor

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
    db = SessionLocal()
    cities = [r[0] for r in db.query(WeatherFeatures.city).distinct()]

    for city in cities:
        rows = (
            db.query(WeatherFeatures)
            .filter(WeatherFeatures.city == city)
            .all()
        )

        X=[]
        y=[]
        for r in rows:
            vals=[getattr(r,f) for f in FEATURES]
            if any(v is None for v in vals):
                continue
            X.append(vals)
            y.append(r.temp)

        if len(X)<500:
            continue

        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            random_state=42
        )
        model.fit(X,y)

        joblib.dump(model,f"{MODEL_DIR}/{city}_gbm.joblib")
        print(f"[MODEL] {city} trained")

    db.close()

if __name__=="__main__":
    train_all()
