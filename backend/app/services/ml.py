from sklearn.linear_model import LinearRegression
import numpy as np
from datetime import datetime
from backend.app.models.weather import Weather

_models={}

def train_city_model(db,city):
    rows=db.query(Weather)\
        .filter(Weather.city==city)\
        .filter(Weather.source=="ERA5")\
        .order_by(Weather.recorded_at)\
        .all()
    if len(rows)<50:
        return None
    X=[]
    y=[]
    temps=[r.temperature for r in rows]
    times=[r.recorded_at for r in rows]
    for i in range(24,len(rows)-1):
        t=times[i]
        X.append([
            t.hour,
            t.timetuple().tm_yday,
            temps[i-1],
            temps[i-2],
            temps[i-24]
        ])
        y.append(temps[i+1])
    model=LinearRegression()
    model.fit(X,y)
    _models[city]=model
    return model

def predict_next_hour(db,city):
    if city not in _models:
        train_city_model(db,city)
    model=_models.get(city)
    if model is None:
        return None
    rows=db.query(Weather)\
        .filter(Weather.city==city)\
        .filter(Weather.source=="ERA5")\
        .order_by(Weather.recorded_at.desc())\
        .limit(24)\
        .all()
    if len(rows)<24:
        return None
    temps=[r.temperature for r in reversed(rows)]
    t=rows[0].recorded_at
    X=[[
        t.hour,
        t.timetuple().tm_yday,
        temps[-1],
        temps[-2],
        temps[0]
    ]]
    return float(model.predict(X)[0])
