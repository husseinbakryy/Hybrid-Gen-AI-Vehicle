from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

MongoClient: Any | None = None

ObjectId: Any | None = None

PyMongoError: type[Exception] = Exception

try:
    import pymongo
    from bson import ObjectId
    from pymongo.errors import PyMongoError

    MongoClient = pymongo.MongoClient
    ObjectId = ObjectId
    PyMongoError = PyMongoError
except ImportError:  # pragma: no cover - optional dependency for local API startup
    MongoClient = None
    ObjectId = None
    PyMongoError = Exception


BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

_CLIENT: Any | None = None


def get_mongo_client() -> Any:
    global _CLIENT
    if _CLIENT is None:
        if MongoClient is None:
            raise RuntimeError("pymongo is not installed. Install Backend requirements to enable MongoDB-backed vehicle endpoints.")

        mongo_uri = os.getenv("MONGODB_URI")
        if not mongo_uri:
            raise ValueError("MONGODB_URI environment variable is not set. Please set it in .env")
        _CLIENT = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    return _CLIENT


def get_vehicles_collection() -> Any | None:
    if MongoClient is None:
        return None

    client = get_mongo_client()
    db_name = os.getenv("MONGODB_DB_NAME", "Vehicles")
    col_name = os.getenv("MONGODB_COLLECTION_NAME", "VehicleSpecs")

    db = client[db_name]
    if col_name in db.list_collection_names() and db[col_name].count_documents({}) > 0:
        return db[col_name]

    # Fallback checks in case database name differs in cluster
    for fallback_db in ["VehicleSpecs", "Vehicle"]:
        f_db = client[fallback_db]
        if col_name in f_db.list_collection_names() and f_db[col_name].count_documents({}) > 0:
            return f_db[col_name]

    return db[col_name]


def _format_vehicle_doc(doc: dict[str, Any]) -> dict[str, Any]:
    specs = doc.get("specifications", {})
    make = doc.get("make", "")
    model = doc.get("model", "")
    vehicle_name = doc.get("vehicleName") or f"{make} {model}".strip()
    body_type = (specs.get("bodyType") or "").lower()
    
    if not body_type:
        archetype = str(doc.get("archetype", "")).lower()
        if "suv" in archetype:
            body_type = "suv"
        elif "sedan" in archetype:
            body_type = "sedan"
        elif "hatchback" in archetype:
            body_type = "hatchback"
        else:
            body_type = "other"

    powertrain_type = (specs.get("powertrainType") or "").lower()
    if not powertrain_type:
        archetype = str(doc.get("archetype", "")).lower()
        if "ev" in archetype:
            powertrain_type = "ev"
        elif "hybrid" in archetype:
            powertrain_type = "hybrid"
        elif "ice" in archetype:
            powertrain_type = "ice"
        else:
            powertrain_type = "hybrid"

    ev_range = round(float(specs.get("nominalEvRangeKm", 0.0)), 1)
    
    # Formatted label suitable for dropdown display
    if ev_range > 0:
        display_label = f"{vehicle_name} ({body_type.upper()} - {ev_range} km EV)"
    else:
        display_label = f"{vehicle_name} ({body_type.upper()})"

    return {
        "id": str(doc.get("_id")),
        "vehicle_name": vehicle_name,
        "name": make,
        "make": make,
        "model": model,
        "body_type": body_type,
        "powertrain_type": powertrain_type,
        "power_train_type": powertrain_type,
        "archetype": doc.get("archetype", f"{powertrain_type}_{body_type}"),
        "ev_range_km": ev_range,
        "display_label": display_label,
        "specifications": specs,
    }


def fetch_vehicles(
    make: str | None = None,
    body_type: str | None = None,
    powertrain_type: str | None = None,
    unique_only: bool = True,
) -> list[dict[str, Any]]:
    col = get_vehicles_collection()
    if col is None:
        return []

    query: dict[str, Any] = {}

    if make:
        query["make"] = {"$regex": f"^{make}$", "$options": "i"}

    if body_type:
        query["$or"] = [
            {"specifications.bodyType": {"$regex": f"^{body_type}$", "$options": "i"}},
            {"archetype": {"$regex": body_type, "$options": "i"}},
        ]

    if powertrain_type:
        powertrain_query = [
            {"specifications.powertrainType": {"$regex": f"^{powertrain_type}$", "$options": "i"}},
            {"archetype": {"$regex": powertrain_type, "$options": "i"}},
        ]
        if "$or" in query:
            query = {"$and": [{"$or": query.pop("$or")}, {"$or": powertrain_query}]}
        else:
            query["$or"] = powertrain_query

    cursor = col.find(query).sort([("make", 1), ("model", 1)])
    formatted = [_format_vehicle_doc(doc) for doc in cursor]

    if not unique_only:
        return formatted

    seen_names: set[str] = set()
    unique_list: list[dict[str, Any]] = []
    for item in formatted:
        v_name = item["vehicle_name"]
        if v_name not in seen_names:
            seen_names.add(v_name)
            unique_list.append(item)

    return unique_list


def fetch_vehicle_by_id(vehicle_id: str) -> dict[str, Any] | None:
    col = get_vehicles_collection()
    if col is None:
        return None
 
    query_id: Any = vehicle_id
    if ObjectId:
        try:
            query_id = ObjectId(vehicle_id)  # Handles MongoDB standard ObjectId format
        except Exception:
            pass
 
    doc = col.find_one({"_id": query_id})
    if not doc and query_id != vehicle_id:
        doc = col.find_one({"_id": vehicle_id}) # Fallback to standard string lookup

    if not doc:
        return None
    return _format_vehicle_doc(doc)


def fetch_vehicle_by_make_model(make: str, model: str) -> dict[str, Any] | None:
    col = get_vehicles_collection()
    if col is None:
        return None

    query = {
        "make": {"$regex": f"^{make}$", "$options": "i"},
        "model": {"$regex": f"^{model}$", "$options": "i"},
    }
    # Retrieve the first document matching make and model
    doc = col.find_one(query)
    if not doc:
        return None
    return _format_vehicle_doc(doc)


def _next_vehicle_id(col: Any) -> str:
    """Generate the next sequential vehicle ID (veh_XXXX)."""
    pipeline = [
        {"$match": {"_id": {"$regex": "^veh_"}}},
        {"$project": {"num": {"$toInt": {"$substr": ["$_id", 4, -1]}}}},
        {"$sort": {"num": -1}},
        {"$limit": 1},
    ]
    results = list(col.aggregate(pipeline))
    next_num = (results[0]["num"] + 1) if results else 1
    return f"veh_{next_num:04d}"


def insert_vehicle(vehicle_data: dict[str, Any]) -> dict[str, Any]:
    """Insert a new vehicle document into MongoDB.

    Expects at minimum: make, model, powertrain_type, body_type.
    Optional but recommended: battery_capacity_kwh, usable_battery_kwh,
    fuel_tank_l, mass_kg, drag_coeff, frontal_area_m2.

    Returns the formatted vehicle document.
    """
    col = get_vehicles_collection()
    if col is None:
        raise RuntimeError("Database collection is not available.")

    make = vehicle_data["make"]
    model = vehicle_data["model"]
    powertrain_type = vehicle_data["powertrain_type"].lower()
    body_type = vehicle_data["body_type"].lower()

    # Sensible defaults for optional technical specs
    battery_cap = float(vehicle_data.get("battery_capacity_kwh", 0.0))
    usable_bat = float(vehicle_data.get("usable_battery_kwh", 0.0))
    fuel_tank = float(vehicle_data.get("fuel_tank_l", 0.0))
    mass_kg = float(vehicle_data.get("mass_kg", 1500.0))
    drag_coeff = float(vehicle_data.get("drag_coeff", 0.28))
    frontal_area = float(vehicle_data.get("frontal_area_m2", 2.3))

    # Auto-zero energy sources that don't apply to the powertrain
    if powertrain_type == "ev":
        fuel_tank = 0.0
    elif powertrain_type == "ice":
        battery_cap = 0.0
        usable_bat = 0.0

    # Derive nominal EV range: usable_battery / 0.16 kWh per km
    nominal_ev_range = round(usable_bat / 0.16, 2) if usable_bat > 0 else 0.0

    vehicle_id = _next_vehicle_id(col)

    doc = {
        "_id": vehicle_id,
        "make": make,
        "model": model,
        "archetype": f"{powertrain_type}_{body_type}",
        "vehicleName": f"{make} {model}",
        "specifications": {
            "powertrainType": powertrain_type,
            "bodyType": body_type,
            "batteryCapacityKwh": battery_cap,
            "usableBatteryKwh": usable_bat,
            "fuelTankL": fuel_tank,
            "massKg": mass_kg,
            "dragCoeff": drag_coeff,
            "frontalAreaM2": frontal_area,
            "rollingResistanceCoeff": 0.008,
            "drivetrainEfficiency": 0.90 if powertrain_type == "ev" else 0.35,
            "regenEfficiency": 0.70 if powertrain_type != "ice" else 0.0,
            "hvacBaseKw": 1.8,
            "cityEfficiencyFactor": 1.0,
            "highwayEfficiencyFactor": 1.0,
            "nominalEvRangeKm": nominal_ev_range,
        },
    }

    col.insert_one(doc)
    return _format_vehicle_doc(doc)




















