import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from backend.app.db.database import SessionLocal
from backend.app.models.weather import Weather

def train_and_predict(city):
    db=SessionLocal()
    rows=db.query(Weather).filter(
        Weather.city==city
    ).order_by(Weather.recorded_at).all()
    db.close()

    if len(rows)<48:
        return {"error":"not enough data"}

    df=pd.DataFrame([{
        "t":i,
        "temp":r.temperature
    } for i,r in enumerate(rows)])

    X=df[["t"]]
    y=df["temp"]

    model=LinearRegression()
    model.fit(X,y)

    future=len(df)+1
    pred=model.predict([[future]])[0]

    trend="stable"
    slope=model.coef_[0]
    if slope>0.01:
        trend="rising"
    elif slope<-0.01:
        trend="falling"

    return {
        "predicted_temperature":round(float(pred),2),
        "trend":trend
    }
