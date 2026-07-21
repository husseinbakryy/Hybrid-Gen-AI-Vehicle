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
 
from database import fetch_vehicle_by_id, fetch_vehicles
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
 
class CompleteTripRequest(BaseModel):
    vehicle_id: str = Field(..., description="MongoDB vehicle ID reference")
    trip_input: dict[str, Any] = Field(..., description="Raw trip features from dashboard")
    user_context: Optional[dict[str, Any]] = Field(default_factory=dict, description="User preferences")
 
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
 
@app.post("/api/agent/recommendation")
def agent_recommendation_endpoint(payload: CompleteTripRequest):
    try:
        # 1. Fetch live specifications from Database
        vehicle_specs = fetch_vehicle_by_id(payload.vehicle_id)
        if not vehicle_specs:
            raise HTTPException(status_code=404, detail=f"Vehicle '{payload.vehicle_id}' not found in database.")
        
        # 2. Extract user input parameters for Model layer
        distance = float(payload.trip_input.get("distance_km", 15.0))
        road = str(payload.trip_input.get("road_type", "urban")).lower()
        ev_range = float(vehicle_specs.get("ev_range_km", 0.0))
        
        # 3. Machine Learning Model Logic Layer
        ml_mode = "ev" if distance <= ev_range and road != "highway" else "hybrid"
        cost = round(distance * (0.05 if ml_mode == "ev" else 0.12), 2)
        co2 = 0.0 if ml_mode == "ev" else round(distance * 0.14, 2)
        
        ml_metrics = {
            "recommended_mode": ml_mode,
            "trip_cost_usd": cost,
            "co2_emissions_kg": co2,
            "battery_depletion_pct": round((distance / max(ev_range, 1.0)) * 100, 1)
        }
        
        # 4. Run the Recommender Agent AI to synthesize everything
        agent_output = run_recommender_agent(
            user_input=payload.trip_input,
            vehicle_data=vehicle_specs,
            ml_metrics=ml_metrics
        )
        
        return {
            "status": "success",
            "vehicle_database_source": vehicle_specs.get("vehicle_name"),
            "ml_inference_metrics": ml_metrics,
            "recommender_agent_response": agent_output
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
 
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)