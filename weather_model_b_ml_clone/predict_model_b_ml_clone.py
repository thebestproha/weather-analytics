import joblib

MODEL_FILE = "model_b_ml_mimic.joblib"


def predict_daily(base, amp, trend, model_file=MODEL_FILE):
    payload = joblib.load(model_file)
    model = payload["model"]

    X = [[float(base), float(amp), float(trend)]]
    mean = [round(float(v), 2) for v in model.predict(X)[0].tolist()]

    return {
        "model_name": payload.get("name", "Model B-ML Mimic"),
        "mean": mean,
        "upper": [round(v + 2, 2) for v in mean],
        "lower": [round(v - 2, 2) for v in mean],
    }


if __name__ == "__main__":
    out = predict_daily(base=28.0, amp=2.5, trend=0.02)
    print(out)
