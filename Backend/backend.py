import sys
import uvicorn
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

MODELS_DIR = REPO_ROOT / "Models"
if str(MODELS_DIR) not in sys.path:
    sys.path.insert(0, str(MODELS_DIR))

from database import fetch_vehicle_by_id, fetch_vehicle_by_make_model, fetch_vehicles
from pipeline.inference import predict_trip_structured
from recommender import run_recommender_agent


class VehicleSummaryItem(BaseModel):
    vehicle_name: str = Field(..., description="Full vehicle name")
    name: str = Field(..., description="Brand / Make name")
    body_type: str = Field(..., description="Body type: sedan, suv, or hatchback")
    power_train_type: str = Field(..., description="Powertrain type: hybrid, ev, or ice")


class VehicleDetailItem(BaseModel):
    id: str = Field(..., description="Unique vehicle ID")
    vehicle_name: str = Field(..., description="Full vehicle name")
    name: str = Field(..., description="Brand / Make name")
    make: str = Field(..., description="Brand / Make")
    model: str = Field(..., description="Model name")
    body_type: str = Field(..., description="Body type")
    powertrain_type: str = Field(..., description="Powertrain type")
    power_train_type: str = Field(..., description="Powertrain type")
    archetype: str = Field(..., description="Vehicle archetype string")
    ev_range_km: float = Field(..., description="Nominal EV range in km")
    display_label: str = Field(..., description="Formatted string for UI")
    specifications: dict[str, Any] = Field(default_factory=dict, description="Detailed technical specifications")


VehicleItem = VehicleDetailItem


class VehicleListResponse(BaseModel):
    total: int = Field(..., description="Total number of vehicles returned")
    vehicles: list[VehicleSummaryItem] = Field(..., description="List of vehicles")


class TripRecommendationRequest(BaseModel):
    trip_input: dict[str, Any] = Field(..., description="Variable trip input parameters including make and model")
    user_context: Optional[dict[str, Any]] = Field(default_factory=dict, description="User context or preferences")


app = FastAPI(
    title="Hybrid Vehicle Recommendation AI API",
    version="1.0.0",
    description="Integrates database specs, ML telemetry, and Agent AI recommendations.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/vehicles", response_model=VehicleListResponse)
def get_vehicles(
    make: Optional[str] = Query(None, description="Filter by vehicle make"),
    body_type: Optional[str] = Query(None, description="Filter by body type"),
    powertrain_type: Optional[str] = Query(None, description="Filter by powertrain type"),
    unique: bool = Query(True, description="Filter to unique vehicle names"),
):
    try:
        vehicles = fetch_vehicles(
            make=make,
            body_type=body_type,
            powertrain_type=powertrain_type,
            unique_only=unique,
        )
        vehicle_items = [VehicleSummaryItem.model_validate(item) for item in vehicles]
        return VehicleListResponse(total=len(vehicle_items), vehicles=vehicle_items)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database query error: {exc}") from exc


@app.get("/api/vehicles/{vehicle_id}", response_model=VehicleItem)
def get_vehicle_by_id(vehicle_id: str):
    try:
        vehicle = fetch_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found.")
        return VehicleDetailItem.model_validate(vehicle)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database query error: {exc}") from exc


@app.post("/api/trip/recommendation")
def trip_recommendation_endpoint(payload: TripRecommendationRequest):
    try:
        trip_input = payload.trip_input
        user_context = payload.user_context or {}

        make = trip_input.get("make")
        model = trip_input.get("model")

        if not make or not model:
            raise HTTPException(status_code=400, detail="Both 'make' and 'model' must be provided in 'trip_input'.")

        dist_km = float(trip_input.get("distance_km", 10.0))
        if dist_km <= 0 or dist_km > 3000:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid distance_km ({dist_km}): must be between 0.1 km and 3,000 km for realistic trip planning.",
            )

        # 1. Fetch vehicle specifications from MongoDB by make & model (returns first matching document)
        vehicle_doc = fetch_vehicle_by_make_model(make, model)
        if not vehicle_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle with make '{make}' and model '{model}' not found in database.",
            )

        specs = vehicle_doc.get("specifications", {})
        ev_range = float(vehicle_doc.get("ev_range_km") or specs.get("nominalEvRangeKm") or 0.0)

        # 2. Build complete 25-feature input dictionary for ML pipeline
        full_ml_features = {
            "make": make,
            "model": model,
            "powertrain_type": specs.get("powertrainType") or vehicle_doc.get("powertrain_type", "hybrid"),
            "body_type": specs.get("bodyType") or vehicle_doc.get("body_type", "sedan"),
            "battery_capacity_kwh": float(specs.get("batteryCapacityKwh", 0.0)),
            "usable_battery_kwh": float(specs.get("usableBatteryKwh", 0.0)),
            "fuel_tank_l": float(specs.get("fuelTankL", 0.0)),
            "mass_kg": float(specs.get("massKg", 0.0)),
            "drag_coeff": float(specs.get("dragCoeff", 0.0)),
            "frontal_area_m2": float(specs.get("frontalAreaM2", 0.0)),
            "city": trip_input.get("city"),
            "season": trip_input.get("season"),
            "weather": trip_input.get("weather"),
            "ambient_temp_c": float(trip_input.get("ambient_temp_c", 20.0)),
            "humidity": float(trip_input.get("humidity", 0.5)),
            "wind_speed_kmh": float(trip_input.get("wind_speed_kmh", 10.0)),
            "precipitation_mm": float(trip_input.get("precipitation_mm", 0.0)),
            "departure_hour": int(trip_input.get("departure_hour", 12)),
            "day_type": trip_input.get("day_type"),
            "trip_purpose": trip_input.get("trip_purpose"),
            "road_type": trip_input.get("road_type"),
            "traffic_level": float(trip_input.get("traffic_level", 0.5)),
            "distance_km": dist_km,
            "passengers": int(trip_input.get("passengers", 1)),
            "cargo_kg": float(trip_input.get("cargo_kg", 0.0)),
        }

        # 3. Run ML Pipeline Inference (predicts all 7 targets)
        ml_results = predict_trip_structured(full_ml_features)

        # Domain Guardrail 1: If trip distance exceeds nominal EV range for a hybrid vehicle, enforce hybrid/ice mode
        powertrain = (specs.get("powertrainType") or vehicle_doc.get("powertrain_type", "")).lower()
        raw_mode = str(ml_results["raw"].get("recommended_mode", "ev")).lower()
        if powertrain == "hybrid" and dist_km > ev_range and raw_mode == "ev":
            ml_results["raw"]["recommended_mode"] = "hybrid"
            ml_results["formatted"]["Recommended Driving Mode"] = "hybrid"

        # Domain Guardrail 2: Dynamic Remaining Range Post-Processing (replaces stagnant ML artifact predictions)
        usable_bat = float(specs.get("usableBatteryKwh") or specs.get("batteryCapacityKwh") or 1.0)
        fuel_tank = float(specs.get("fuelTankL") or 0.0)
        bat_used = float(ml_results["raw"].get("battery_used_kwh", 0.0))
        fuel_used = float(ml_results["raw"].get("fuel_used_l", 0.0))

        bat_pct_left = max(0.0, (usable_bat - min(bat_used, usable_bat)) / max(usable_bat, 1e-3))
        rem_ev = bat_pct_left * ev_range
        fuel_pct_left = max(0.0, (fuel_tank - min(fuel_used, fuel_tank)) / max(fuel_tank, 1e-3)) if fuel_tank > 0 else 0.0
        rem_fuel = fuel_pct_left * fuel_tank * 12.0
        calc_range_left = round(rem_ev + rem_fuel, 2)

        # Apply dynamic calculated range if ML model range is stagnant or unrealistic
        ml_range = float(ml_results["raw"].get("range_left_km", 0.0))
        if abs(ml_range - 11.23) < 1.0 or ml_range <= 0 or calc_range_left != ml_range:
            ml_results["raw"]["range_left_km"] = calc_range_left
            ml_results["formatted"]["Predicted Remaining Range"] = f"{calc_range_left:.2f} km"


        # 4. Synthesize with GenAI Recommender Agent
        agent_recommendation = run_recommender_agent(
            user_input=trip_input,
            vehicle_data=vehicle_doc,
            ml_metrics=ml_results,
            user_context=user_context,
        )

        return {
            "status": "success",
            "vehicle": vehicle_doc,
            "trip_input": trip_input,
            "user_context": user_context,
            "pipeline_predictions": ml_results,
            "agent_recommendation": agent_recommendation,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc



if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)