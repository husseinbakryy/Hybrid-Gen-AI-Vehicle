from pathlib import Path

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



def predict_trip(input_data_dict: dict, artifact_dir: str | Path = ARTIFACT_DIR):
    preprocessor, models = load_assets(artifact_dir)

    missing_features = [feature for feature in FEATURES if feature not in input_data_dict]
    if missing_features:
        raise ValueError(f"Missing required input features: {missing_features}")

    input_df = pd.DataFrame([{feature: input_data_dict[feature] for feature in FEATURES}])
    transformed = preprocessor.transform(input_df)

    pred_mode = models["m1_recommended_mode"].predict(transformed)[0]
    pred_fuel = models["m2_fuel_consumption"].predict(transformed)[0]
    pred_battery = models["m3_battery_energy"].predict(transformed)[0]
    pred_co2 = models["m4_co2_emissions"].predict(transformed)[0]
    pred_cost = models["m5_trip_cost"].predict(transformed)[0]

    return {
        "Recommended Driving Mode": pred_mode,
        "Predicted Fuel Consumption": f"{pred_fuel:.2f} Liters",
        "Predicted Battery Energy Used": f"{pred_battery:.2f} kWh",
        "Predicted Carbon Footprint": f"{pred_co2:.2f} kg of CO2",
        "Predicted Financial Trip Cost": f"${pred_cost:.2f} USD",
    }
