# Backend API

FastAPI service that accepts dashboard trip inputs, fetches vehicle specs from MongoDB, runs ML inference from `Models`, and generates GenAI recommendations.

## Endpoints

- `GET /health`
- `GET /api/vehicles` (supports optional query params: `make`, `body_type`, `powertrain_type`)
- `GET /api/vehicles/{vehicle_id}`
- `POST /api/trip/recommendation`

## Run

```powershell
cd Backend
py -m pip install -r requirements.txt
py -m uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
```

Open [http://localhost:8000](http://localhost:8000) or [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser (interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs)).


## Environment Variables (.env)

```env
MONGODB_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/
MONGODB_DB_NAME=Vehicles
MONGODB_COLLECTION_NAME=VehicleSpecs
OPENROUTER_API_KEY=your_key_here
```

## Sample Response: `GET /api/vehicles`

```json
{
  "total": 60,
  "vehicles": [
    {
      "id": "veh_0020",
      "vehicle_name": "Orion Pulse H",
      "make": "Orion",
      "model": "Pulse H",
      "body_type": "sedan",
      "powertrain_type": "hybrid",
      "archetype": "hybrid_sedan",
      "ev_range_km": 85.8,
      "display_label": "Orion Pulse H (SEDAN - 85.8 km EV)",
      "specifications": {
        "powertrainType": "hybrid",
        "bodyType": "sedan",
        "batteryCapacityKwh": 12.027,
        "usableBatteryKwh": 7.873,
        "fuelTankL": 42.074,
        "massKg": 1686.13,
        "dragCoeff": 0.243,
        "frontalAreaM2": 2.406,
        "rollingResistanceCoeff": 0.0081,
        "drivetrainEfficiency": 0.420,
        "regenEfficiency": 0.736,
        "hvacBaseKw": 1.583,
        "cityEfficiencyFactor": 1.153,
        "highwayEfficiencyFactor": 0.980,
        "nominalEvRangeKm": 85.788
      }
    }
  ]
}
```
