from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

MongoClient: Any | None = None
PyMongoError: type[Exception] = Exception

try:
    _mongo_mod = importlib.import_module("pymongo")
    MongoClient = _mongo_mod.MongoClient
    PyMongoError = _mongo_mod.errors.PyMongoError
except ImportError:  # pragma: no cover - optional dependency for local API startup
    MongoClient = None
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

    doc = col.find_one({"_id": vehicle_id})
    if not doc:
        return None
    return _format_vehicle_doc(doc)
