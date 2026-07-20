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
from recommender import generate_recommendation


class VehicleSummaryItem(BaseModel):
    vehicle_name: str = Field(..., description="Full vehicle name (e.g. Orion Pulse H)")
    name: str = Field(..., description="Brand / Make name of the vehicle (e.g. Orion)")
    body_type: str = Field(..., description="Body type: sedan, suv, or hatchback")
    power_train_type: str = Field(..., description="Powertrain type: hybrid, ev, or ice")


class VehicleDetailItem(BaseModel):
    id: str = Field(..., description="Unique vehicle ID in MongoDB (e.g. veh_0020)")
    vehicle_name: str = Field(..., description="Full vehicle name (e.g. Orion Pulse H)")
    name: str = Field(..., description="Brand / Make name of the vehicle (e.g. Orion)")
    make: str = Field(..., description="Brand / Make of the vehicle (e.g. Orion)")
    model: str = Field(..., description="Model name of the vehicle (e.g. Pulse H)")
    body_type: str = Field(..., description="Body type: sedan, suv, or hatchback")
    powertrain_type: str = Field(..., description="Powertrain type: hybrid, ev, or ice")
    power_train_type: str = Field(..., description="Powertrain type: hybrid, ev, or ice")
    archetype: str = Field(..., description="Vehicle archetype string (e.g. hybrid_sedan)")
    ev_range_km: float = Field(..., description="Nominal EV range in km")
    display_label: str = Field(..., description="Formatted string ready for UI dropdown menus")
    specifications: dict[str, Any] = Field(default_factory=dict, description="Detailed technical specifications")


VehicleItem = VehicleDetailItem


class VehicleListResponse(BaseModel):
    total: int = Field(..., description="Total number of vehicles returned")
    vehicles: list[VehicleSummaryItem] = Field(..., description="List of vehicles containing summary fields only")


class TripRecommendationRequest(BaseModel):
    trip_input: dict[str, Any] = Field(
        ...,
        description="Raw trip features coming from dashboard form or client-side mapping.",
    )
    user_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional user preferences, constraints, and session metadata.",
    )


app = FastAPI(
    title="Hybrid Vehicle Recommendation API",
    version="0.2.0",
    description="Accepts dashboard trip inputs, fetches MongoDB vehicle specs, runs ML models, and returns recommendations.",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/vehicles", response_model=VehicleListResponse)
def get_vehicles(
    make: Optional[str] = Query(None, description="Filter by vehicle make/brand (e.g. Orion, Aster)"),
    body_type: Optional[str] = Query(None, description="Filter by body type (e.g. sedan, suv, hatchback)"),
    powertrain_type: Optional[str] = Query(None, description="Filter by powertrain type (e.g. hybrid, ev, ice)"),
    unique: bool = Query(True, description="Filter to unique vehicle names only (default: True)"),
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
    except RuntimeError as exc:
        return VehicleListResponse(
            total=0,
            vehicles=[],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database query error: {exc}") from exc


@app.get("/api/vehicles/{vehicle_id}", response_model=VehicleItem)
def get_vehicle_by_id(vehicle_id: str):
    try:
        vehicle = fetch_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found.")
        return VehicleDetailItem.model_validate(vehicle)
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Vehicle database dependency is not available in the current backend environment.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database query error: {exc}") from exc


@app.post("/api/trip/recommendation")
async def recommend_trip(request: TripRecommendationRequest):
    try:
        ml_results = {"recommended_mode": "ev", "cost": 1.5}
        advice = generate_recommendation(
            trip_input=request.trip_input,
            ml_output=ml_results,
            user_context=request.user_context,
        )
        return {"ml_results": ml_results, "ai_advice": advice}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
