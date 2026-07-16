# Backend API

FastAPI service that accepts dashboard trip inputs, runs ML inference from `Models`, then generates a GenAI recommendation.

## Endpoints

- `GET /health`
- `POST /api/trip/recommendation`

## Run

```powershell
cd Backend
py -m pip install -r requirements.txt
py -m uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
```

## Request Body

```json
{
  "trip_input": {
    "make": "Nexa",
    "model": "VoltMini",
    "powertrain_type": "ev",
    "body_type": "hatchback",
    "battery_capacity_kwh": 53.0,
    "usable_battery_kwh": 48.6,
    "fuel_tank_l": 2.5,
    "mass_kg": 1619.0,
    "drag_coeff": 0.26,
    "frontal_area_m2": 2.3,
    "city": "Chicago",
    "season": "fall",
    "weather": "clear",
    "ambient_temp_c": 19.0,
    "humidity": 0.72,
    "wind_speed_kmh": 17.2,
    "precipitation_mm": 0.9,
    "departure_hour": 10,
    "day_type": "weekday",
    "trip_purpose": "business",
    "road_type": "highway",
    "traffic_level": 0.9,
    "distance_km": 38.0,
    "passengers": 1,
    "cargo_kg": 26.4
  },
  "user_context": {
    "comfort_priority": "balanced"
  }
}
```

## Response Body

Returns:
- Original input
- ML output (`raw` + `formatted`)
- GenAI recommendation
