"""
Quick commands reference for weather data pipeline
"""

COMMANDS = {
    "1. Create Database": {
        "cmd": "python -m app.db.init_db",
        "desc": "Creates weather and weather_features tables"
    },
    
    "2. Ingest Data": {
        "cmd": "python -m app.services.meteostat_bulk_runner",
        "desc": "Runs Meteostat hourly ingestion (configured in file)"
    },
    
    "3. Validate Data": {
        "cmd": "python debug/data_stats.py",
        "desc": "Shows yearly/monthly counts and coverage"
    },
    
    "4. Check Hourly Balance": {
        "cmd": "python debug/hourly_stats.py",
        "desc": "Shows hour-of-day distribution (critical for diurnal)"
    },
    
    "5. Analyze Gaps": {
        "cmd": "python debug/missing_data.py",
        "desc": "Identifies missing data patterns and gaps"
    },
    
    "6. Build Features": {
        "cmd": "python -m app.services.feature_builder",
        "desc": "Engineers ML features from raw weather data"
    },
    
    "7. Train Models": {
        "cmd": "python -m app.services.train_models",
        "desc": "Trains GBM models for each city"
    }
}

if __name__ == "__main__":
    print("\n" + "="*70)
    print("WEATHER ANALYTICS PIPELINE - COMMAND REFERENCE")
    print("="*70 + "\n")
    
    for step, info in COMMANDS.items():
        print(f"{step}")
        print(f"  Command: {info['cmd']}")
        print(f"  Purpose: {info['desc']}")
        print()
    
    print("="*70)
    print("Working directory: backend/")
    print("="*70 + "\n")
