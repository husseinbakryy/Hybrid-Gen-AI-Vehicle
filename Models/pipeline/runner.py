import time
from pathlib import Path

import joblib

from .config import ARTIFACT_DIR, MODEL_ASSETS, PREPROCESSOR_FILE, TARGET_MAP
from .data import load_dataset, prepare_data
from .inference import predict_trip
from .model_battery import train_battery_model
from .model_cost import train_cost_model
from .model_emissions import train_emissions_model
from .model_fuel import train_fuel_model
from .model_mode import train_mode_model
from .model_range import train_range_model
from .model_time import train_time_model


def run_pipeline(data_path: str | Path | None = None, artifact_dir: str | Path = ARTIFACT_DIR):
    started_at = time.time()
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    print("Initializing model training pipeline...")
    df = load_dataset(data_path)
    print(f"Dataset loaded with shape: {df.shape}")

    prepared = prepare_data(df)
    joblib.dump(prepared.preprocessor, artifact_dir / PREPROCESSOR_FILE)
    print(f"Saved preprocessor to: {artifact_dir / PREPROCESSOR_FILE}")

    metrics = {}

    mode_model, metrics["m1_recommended_mode"] = train_mode_model(
        prepared.X_train,
        prepared.X_test,
        prepared.y_train[TARGET_MAP["m1_recommended_mode"]],
        prepared.y_test[TARGET_MAP["m1_recommended_mode"]],
    )
    joblib.dump(mode_model, artifact_dir / MODEL_ASSETS["m1_recommended_mode"])

    fuel_model, metrics["m2_fuel_consumption"] = train_fuel_model(
        prepared.X_train,
        prepared.X_test,
        prepared.y_train[TARGET_MAP["m2_fuel_consumption"]],
        prepared.y_test[TARGET_MAP["m2_fuel_consumption"]],
    )
    joblib.dump(fuel_model, artifact_dir / MODEL_ASSETS["m2_fuel_consumption"])

    battery_model, metrics["m3_battery_energy"] = train_battery_model(
        prepared.X_train,
        prepared.X_test,
        prepared.y_train[TARGET_MAP["m3_battery_energy"]],
        prepared.y_test[TARGET_MAP["m3_battery_energy"]],
    )
    joblib.dump(battery_model, artifact_dir / MODEL_ASSETS["m3_battery_energy"])

    emissions_model, metrics["m4_co2_emissions"] = train_emissions_model(
        prepared.X_train,
        prepared.X_test,
        prepared.y_train[TARGET_MAP["m4_co2_emissions"]],
        prepared.y_test[TARGET_MAP["m4_co2_emissions"]],
    )
    joblib.dump(emissions_model, artifact_dir / MODEL_ASSETS["m4_co2_emissions"])

    cost_model, metrics["m5_trip_cost"] = train_cost_model(
        prepared.X_train,
        prepared.X_test,
        prepared.y_train[TARGET_MAP["m5_trip_cost"]],
        prepared.y_test[TARGET_MAP["m5_trip_cost"]],
    )
    joblib.dump(cost_model, artifact_dir / MODEL_ASSETS["m5_trip_cost"])

    range_model, metrics["m6_range_left"] = train_range_model(
        prepared.X_train,
        prepared.X_test,
        prepared.y_train[TARGET_MAP["m6_range_left"]],
        prepared.y_test[TARGET_MAP["m6_range_left"]],
    )
    joblib.dump(range_model, artifact_dir / MODEL_ASSETS["m6_range_left"])

    time_model, metrics["m7_trip_time"] = train_time_model(
        prepared.X_train,
        prepared.X_test,
        prepared.y_train[TARGET_MAP["m7_trip_time"]],
        prepared.y_test[TARGET_MAP["m7_trip_time"]],
    )
    joblib.dump(time_model, artifact_dir / MODEL_ASSETS["m7_trip_time"])

    print("Training completed. Metrics summary:")
    for model_name, model_metrics in metrics.items():
        print(f"- {model_name}: {model_metrics}")

    sample_profile = prepared.X_test_raw.iloc[0].to_dict()
    prediction = predict_trip(sample_profile, artifact_dir=artifact_dir)

    print("Sample prediction output:")
    for key, value in prediction.items():
        print(f"  {key}: {value}")

    elapsed = time.time() - started_at
    print(f"Pipeline finished in {elapsed:.2f} seconds")

    return {
        "metrics": metrics,
        "sample_prediction": prediction,
        "artifact_dir": str(artifact_dir),
        "elapsed_seconds": elapsed,
    }
