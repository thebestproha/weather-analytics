from fastapi import FastAPI

app = FastAPI(
    title="Weather Analytics API",
    version="1.0.0"
)

@app.get("/")
def health_check():
    return {"status":"ok"}
