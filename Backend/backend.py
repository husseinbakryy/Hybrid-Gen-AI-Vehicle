from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import sys

from fastapi import FastAPI, HTTPException, Query
from dotenv import load_dotenv
from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

MODELS_DIR = REPO_ROOT / "Models"
if str(MODELS_DIR) not in sys.path:
    sys.path.insert(0, str(MODELS_DIR))

from pipeline.config import FEATURES
from pipeline.inference import predict_trip_structured, load_assets
from recommender import generate_recommendation
from database import fetch_vehicles, fetch_vehicle_by_id


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


class TripRecommendationResponse(BaseModel):
    request_id: str
    timestamp_utc: str
    input: dict[str, Any]
    ml_output: dict[str, Any]
    genai_recommendation: dict[str, Any]


app = FastAPI(
    title="Hybrid Vehicle Recommendation API",
    version="0.2.0",
    description="Accepts dashboard trip inputs, fetches MongoDB vehicle specs, runs ML models, and returns recommendations.",
)


_ASSETS: tuple[Any, dict[str, Any]] | None = None


def _get_assets():
    global _ASSETS
    if _ASSETS is None:
        _ASSETS = load_assets()
    return _ASSETS


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
    """
    Fetch vehicle options from MongoDB (VehicleSpecs collection) for UI drop-down selection.
    Returns unique vehicle names, make (name), body type (SUV, Sedan, etc.), powertrain type, EV range, and specifications.
    """
    try:
        vehicles = fetch_vehicles(
            make=make,
            body_type=body_type,
            powertrain_type=powertrain_type,
            unique_only=unique,
        )
        return VehicleListResponse(total=len(vehicles), vehicles=vehicles)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database query error: {exc}") from exc


@app.get("/api/vehicles/{vehicle_id}", response_model=VehicleItem)
def get_vehicle_by_id(vehicle_id: str):
    """
    Fetch full details and specifications for a single vehicle by ID.
    """
    try:
        vehicle = fetch_vehicle_by_id(vehicle_id)
        if not vehicle:
            raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found.")
        return vehicle
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database query error: {exc}") from exc


@app.post("/api/trip/recommendation", response_model=TripRecommendationResponse)
def recommend_trip(request: TripRecommendationRequest):
    missing_features = [feature for feature in FEATURES if feature not in request.trip_input]
    if missing_features:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Missing required trip_input features.",
                "missing_features": missing_features,
            },
        )

    try:
        preprocessor, models = _get_assets()
        ml_bundle = predict_trip_structured(
            request.trip_input,
            preprocessor=preprocessor,
            models=models,
        )
        recommendation = generate_recommendation(
            trip_input=request.trip_input,
            ml_output=ml_bundle["raw"],
            user_context=request.user_context,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Model artifacts unavailable: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected API error: {exc}") from exc

    request_id = datetime.now(timezone.utc).strftime("REQ-%Y%m%d%H%M%S%f")

    return TripRecommendationResponse(
        request_id=request_id,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        input=request.trip_input,
        ml_output={
            "raw": ml_bundle["raw"],
            "formatted": ml_bundle["formatted"],
        },
        genai_recommendation=recommendation,
    )
