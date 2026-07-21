from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .config import ARTIFACT_DIR, FEATURES, MODEL_ASSETS, PREPROCESSOR_FILE



def _asset_path(artifact_dir: str | Path, filename: str) -> Path:
    return Path(artifact_dir) / filename



def load_assets(artifact_dir: str | Path = ARTIFACT_DIR):
    artifact_dir = Path(artifact_dir)

    preprocessor_path = _asset_path(artifact_dir, PREPROCESSOR_FILE)
    if not preprocessor_path.exists():
        raise FileNotFoundError(f"Missing preprocessor: {preprocessor_path}")

    preprocessor = joblib.load(preprocessor_path)
    models = {}

    for key, filename in MODEL_ASSETS.items():
        model_path = _asset_path(artifact_dir, filename)
        if not model_path.exists():
            raise FileNotFoundError(f"Missing model artifact: {model_path}")
        models[key] = joblib.load(model_path)

    return preprocessor, models



def predict_trip_structured(
    input_data_dict: dict[str, Any],
    artifact_dir: str | Path = ARTIFACT_DIR,
    preprocessor=None,
    models=None,
):
    if preprocessor is None or models is None:
        preprocessor, models = load_assets(artifact_dir)

    missing_features = [feature for feature in FEATURES if feature not in input_data_dict]
    if missing_features:
        raise ValueError(f"Missing required input features: {missing_features}")

    input_df = pd.DataFrame([{feature: input_data_dict[feature] for feature in FEATURES}])
    transformed = preprocessor.transform(input_df)

    pred_mode = models["m1_recommended_mode"].predict(transformed)[0]
    pred_fuel = float(models["m2_fuel_consumption"].predict(transformed)[0])
    pred_battery = float(models["m3_battery_energy"].predict(transformed)[0])
    pred_co2 = float(models["m4_co2_emissions"].predict(transformed)[0])
    pred_cost = float(models["m5_trip_cost"].predict(transformed)[0])
    pred_range_left = float(models["m6_range_left"].predict(transformed)[0])
    pred_trip_time = float(models["m7_trip_time"].predict(transformed)[0])

    raw = {
        "recommended_mode": str(pred_mode),
        "fuel_used_l": pred_fuel,
        "battery_used_kwh": pred_battery,
        "co2_emissions_kg": pred_co2,
        "trip_cost_usd": pred_cost,
        "range_left_km": pred_range_left,
        "trip_time_min": pred_trip_time,
    }

    formatted = {
        "Recommended Driving Mode": raw["recommended_mode"],
        "Predicted Fuel Consumption": f"{raw['fuel_used_l']:.2f} Liters",
        "Predicted Battery Energy Used": f"{raw['battery_used_kwh']:.2f} kWh",
        "Predicted Carbon Footprint": f"{raw['co2_emissions_kg']:.2f} kg of CO2",
        "Predicted Financial Trip Cost": f"${raw['trip_cost_usd']:.2f} USD",
        "Predicted Remaining Range": f"{raw['range_left_km']:.2f} km",
        "Predicted Trip Duration": f"{raw['trip_time_min']:.2f} Minutes",
    }

    return {"raw": raw, "formatted": formatted}



def predict_trip(input_data_dict: dict, artifact_dir: str | Path = ARTIFACT_DIR):
    return predict_trip_structured(input_data_dict, artifact_dir=artifact_dir)["formatted"]
