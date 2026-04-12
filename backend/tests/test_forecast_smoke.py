from app.db.database import SessionLocal
from app.services.final_forecast import get_final_forecast


def test_forecast_schema_smoke():
    db = SessionLocal()
    try:
        result = get_final_forecast("Chennai", db, long_model="b")
    finally:
        db.close()

    assert "meta" in result
    assert "current" in result
    assert "hourly" in result
    assert "daily" in result

    assert len(result["hourly"]) == 24
    assert len(result["daily"]["mean"]) == 7
