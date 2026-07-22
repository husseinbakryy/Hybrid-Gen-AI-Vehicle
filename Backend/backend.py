import sys
import uvicorn
from pathlib import Path
from typing import Any, Optional
import io
import tempfile
from gtts import gTTS

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

MODELS_DIR = REPO_ROOT / "Models"
if str(MODELS_DIR) not in sys.path:
    sys.path.insert(0, str(MODELS_DIR))

try:
    from .database import fetch_vehicle_by_id, fetch_vehicle_by_make_model, fetch_vehicles
    from .play_audio import play_audio_file
    from .recommender import run_recommender_agent
except ImportError:  # pragma: no cover - supports direct script execution
    from database import fetch_vehicle_by_id, fetch_vehicle_by_make_model, fetch_vehicles
    from play_audio import play_audio_file
    from recommender import run_recommender_agent

try:
    from pipeline.inference import predict_trip_structured
except ImportError:
    predict_trip_structured = None

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
    trip_input: dict[str, Any] = Field(..., description="Variable trip input parameters including make, model, and distance_km")
    user_context: Optional[dict[str, Any]] = Field(default_factory=dict, description="User context or preferences")
    vehicle_id: Optional[str] = Field(default=None, description="Optional unique vehicle ID lookup")

def _normalize_trip_payload(payload: Any) -> tuple[dict[str, Any], dict[str, Any], Optional[str]]:
    if isinstance(payload, TripRecommendationRequest):
        payload_dict = payload.model_dump()
    elif isinstance(payload, dict):
        payload_dict = payload
    elif hasattr(payload, "model_dump"):
        payload_dict = payload.model_dump()
    else:
        payload_dict = {}

    trip_input = payload_dict.get("trip_input", {}) if isinstance(payload_dict.get("trip_input"), dict) else {}
    if not isinstance(trip_input, dict):
        trip_input = {}

    user_context = payload_dict.get("user_context") or {}
    if not isinstance(user_context, dict):
        user_context = {}

    if not trip_input and isinstance(payload_dict, dict):
        trip_input = {
            key: value
            for key, value in payload_dict.items()
            if key not in {"user_context", "vehicle_id"}
        }
        if "user_context" in payload_dict and isinstance(payload_dict.get("user_context"), dict):
            user_context = payload_dict["user_context"]

    vehicle_id = payload_dict.get("vehicle_id") or trip_input.get("vehicle_id")
    return trip_input, user_context, vehicle_id

def _compute_smart_fallback(features: dict[str, Any]) -> dict[str, Any]:
    """Computes realistic estimates if the ML pipeline model file is missing."""
    dist = float(features.get("distance_km", 10.0))
    ptype = str(features.get("powertrain_type", "hybrid")).lower()
    
    # Rough estimations based on powertrain type and distance
    if "ev" in ptype:
        fuel_l = 0.0
        batt_kwh = round(dist * 0.18, 2)  # ~18 kWh per 100km
        co2 = 0.0
        cost = round(batt_kwh * 0.15, 2)   # Electricity cost estimate
    elif "hybrid" in ptype:
        fuel_l = round(dist * 0.045, 2)   # ~4.5 L per 100km
        batt_kwh = round(dist * 0.05, 2)
        co2 = round(fuel_l * 2.31, 2)     # ~2.31 kg CO2 per liter of gasoline
        cost = round((fuel_l * 1.40) + (batt_kwh * 0.15), 2)
    else:  # ICE
        fuel_l = round(dist * 0.075, 2)   # ~7.5 L per 100km
        batt_kwh = 0.0
        co2 = round(fuel_l * 2.31, 2)
        cost = round(fuel_l * 1.40, 2)

    trip_time = round((dist / 60.0) * 60, 1)  # Estimated minutes assuming average city/highway blend

    return {
        "raw": {
            "recommended_mode": ptype if ptype in ["ev", "hybrid"] else "hybrid",
            "fuel_used_l": fuel_l,
            "battery_used_kwh": batt_kwh,
            "co2_emissions_kg": co2,
            "trip_cost_usd": cost,
            "range_left_km": round(max(0.0, 500.0 - dist), 1),
            "trip_time_min": trip_time,
        },
        "formatted": {
            "Recommended Driving Mode": ptype.upper(),
            "Predicted Fuel Consumption": f"{fuel_l:.2f} Liters",
            "Predicted Battery Energy Used": f"{batt_kwh:.2f} kWh",
            "Predicted Carbon Footprint": f"{co2:.2f} kg of CO2",
            "Predicted Financial Trip Cost": f"${cost:.2f} USD",
            "Predicted Remaining Range": "500.00 km",
            "Predicted Trip Duration": f"{trip_time:.1f} Minutes",
        },
        "fallback_reason": "ML model file not found; generated via intelligent estimation parameters."
    }

app = FastAPI(
    title="Hybrid Vehicle Recommendation AI API",
    version="1.1.0",
    description="Clean API endpoints with input parameters, structured ML/Agent output, and gTTS audio synthesis.",
)

LATEST_AUDIO_PATH: Optional[Path] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/audio/latest")
def get_latest_audio():
    global LATEST_AUDIO_PATH
    if not LATEST_AUDIO_PATH or not LATEST_AUDIO_PATH.exists():
        raise HTTPException(status_code=404, detail="No audio file available yet.")
    return FileResponse(path=LATEST_AUDIO_PATH, media_type="audio/mp3", filename="trip_recommendation.mp3")

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
    global LATEST_AUDIO_PATH
    try:
<<<<<<< Updated upstream
        trip_input = payload.trip_input
      
        user_context = payload.user_context or {}
=======
        trip_input, user_context, vehicle_id = _normalize_trip_payload(payload)
>>>>>>> Stashed changes

        make = trip_input.get("make")
        model = trip_input.get("model")
        vehicle_doc = None

        if not make or not model:
            if vehicle_id:
                vehicle_doc = fetch_vehicle_by_id(vehicle_id)
                if vehicle_doc:
                    make = vehicle_doc.get("make")
                    model = vehicle_doc.get("model")
            if not make or not model:
                raise HTTPException(status_code=400, detail="Both 'make' and 'model' must be provided in 'trip_input' or a valid 'vehicle_id' must be supplied.")

        dist_km = float(trip_input.get("distance_km", 10.0))
        if dist_km <= 0 or dist_km > 3000:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid distance_km ({dist_km}): must be between 0.1 km and 3,000 km for realistic trip planning.",
            )

        if not vehicle_doc:
            vehicle_doc = fetch_vehicle_by_make_model(make, model)
        if not vehicle_doc:
            raise HTTPException(
                status_code=404,
                detail=f"Vehicle with make '{make}' and model '{model}' not found in database.",
            )

        specs = vehicle_doc.get("specifications", {})

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

        ml_results = None
        if predict_trip_structured is not None:
            try:
                ml_results = predict_trip_structured(full_ml_features)
            except Exception:
                ml_results = None

<<<<<<< Updated upstream
        # 3b. Refine trip time using user-supplied avg_speed_kmh
        avg_speed = float(trip_input.get("avg_speed_kmh", 0.0))
        if avg_speed > 0 and dist_km > 0:
            base_time_min = (dist_km / avg_speed) * 60.0
            traffic = float(trip_input.get("traffic_level", 0.0))
            traffic_multiplier = 1.0 + 0.5 * traffic          # 0→×1.0 … 1→×1.5
            refined_time = round(base_time_min * traffic_multiplier, 2)
            ml_results["raw"]["trip_time_min"] = refined_time
            ml_results["formatted"]["Predicted Trip Duration"] = f"{refined_time:.2f} Minutes"
=======
        if not ml_results:
            ml_results = _compute_smart_fallback(full_ml_features)
>>>>>>> Stashed changes

        agent_recommendation = run_recommender_agent(
            user_input=trip_input,
            vehicle_data=vehicle_doc,
            ml_metrics=ml_results,
            user_context=user_context,
        )

        try:
            summary_text = agent_recommendation.get("summary")
            if isinstance(summary_text, dict):
                summary_text = summary_text.get("text", "Here is your trip recommendation.")
            elif not summary_text:
                summary_text = "Trip recommendation generated successfully by the AI agent."

            tts = gTTS(text=str(summary_text), lang='en', slow=False)
            audio_fp = io.BytesIO()
            tts.write_to_fp(audio_fp)
            audio_fp.seek(0)
            
            raw_bytes = audio_fp.read()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
                temp_audio.write(raw_bytes)
                LATEST_AUDIO_PATH = Path(temp_audio.name)

            try:
                play_audio_file(LATEST_AUDIO_PATH)
            except Exception:
                pass

        except Exception as audio_exc:
            print(f"Audio generation warning: {audio_exc}")

        return {
            "input": {
                "trip_input": trip_input,
                "user_context": user_context,
                "vehicle_id": vehicle_id,
            },
            "output": {
                "status": "success",
                "vehicle": vehicle_doc,
                "pipeline_predictions": ml_results,
                "ml_results": ml_results,
                "agent_recommendation": agent_recommendation,
                "ml_fallback_used": "fallback_reason" in ml_results,
            },
            "play_audio": {
                "format": "mp3",
                "audio_ready": True,
                "audio_url": "/api/audio/latest"
            }
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)