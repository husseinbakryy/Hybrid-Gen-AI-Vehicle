from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .config import (
    ARTIFACT_DIR,
    AVG_FUEL_ECONOMY_KM_PER_L,
    CO2_PER_KWH_GRID,
    CO2_PER_LITER_FUEL,
    ELEC_PRICE_PER_KWH,
    EV_CONSUMPTION_KWH_PER_KM,
    FEATURES,
    FUEL_PRICE_PER_LITER,
    MAX_SPEED_KMH,
    MODEL_ASSETS,
    PREPROCESSOR_FILE,
)



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


# ---------------------------------------------------------------------------
# Post-prediction consistency layer
# ---------------------------------------------------------------------------

def _enforce_consistency(
    raw: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    """Apply domain / physics rules so the 7 independently-predicted targets
    are mutually consistent.  Operates on the *raw* prediction dict returned
    by the models and returns a corrected copy.

    Rules applied (in order):
      1. Non-negativity
      2. Powertrain-energy exclusion
      3. Mode-energy alignment
      4. Capacity capping
      5. CO₂ re-derivation from energy
      6. Cost re-derivation from energy
      7. Physics-based remaining range
      8. Trip-time floor
    """
    out = dict(raw)  # shallow copy

    # --- Extract vehicle / trip attributes from the input features ----------
    powertrain = str(inputs.get("powertrain_type", "")).lower()
    usable_bat = float(inputs.get("usable_battery_kwh", 0.0))
    fuel_tank = float(inputs.get("fuel_tank_l", 0.0))
    distance_km = float(inputs.get("distance_km", 0.0))

    # Derive nominal EV range from battery capacity & consumption rate
    nominal_ev_range = usable_bat / EV_CONSUMPTION_KWH_PER_KM if usable_bat > 0 else 0.0

    # --- 1. Non-negativity --------------------------------------------------
    for key in ("fuel_used_l", "battery_used_kwh", "co2_emissions_kg",
                "trip_cost_usd", "range_left_km", "trip_time_min"):
        out[key] = max(0.0, float(out.get(key, 0.0)))

    # --- 2. Powertrain-energy exclusion -------------------------------------
    if powertrain == "ev":
        out["fuel_used_l"] = 0.0
    elif powertrain == "ice":
        out["battery_used_kwh"] = 0.0

    # --- 3. Mode-energy alignment -------------------------------------------
    mode = str(out.get("recommended_mode", "")).lower()

    # Override impossible mode for the powertrain first
    if powertrain == "ev" and mode == "ice":
        out["recommended_mode"] = "ev"
        mode = "ev"
    elif powertrain == "ice" and mode == "ev":
        out["recommended_mode"] = "ice"
        mode = "ice"

    # For hybrids: if distance > EV range and mode is EV, switch to hybrid
    if powertrain == "hybrid" and mode == "ev" and distance_km > nominal_ev_range > 0:
        out["recommended_mode"] = "hybrid"
        mode = "hybrid"

    # Enforce energy zeros consistent with (corrected) mode
    if mode == "ev":
        out["fuel_used_l"] = 0.0
    elif mode == "ice":
        out["battery_used_kwh"] = 0.0

    # --- 4. Capacity capping ------------------------------------------------
    if usable_bat > 0:
        out["battery_used_kwh"] = min(out["battery_used_kwh"], usable_bat)
    if fuel_tank > 0:
        out["fuel_used_l"] = min(out["fuel_used_l"], fuel_tank)

    # --- 5. CO₂ re-derivation -----------------------------------------------
    out["co2_emissions_kg"] = round(
        out["fuel_used_l"] * CO2_PER_LITER_FUEL
        + out["battery_used_kwh"] * CO2_PER_KWH_GRID,
        4,
    )

    # --- 6. Cost re-derivation ----------------------------------------------
    out["trip_cost_usd"] = round(
        out["fuel_used_l"] * FUEL_PRICE_PER_LITER
        + out["battery_used_kwh"] * ELEC_PRICE_PER_KWH,
        4,
    )

    # --- 7. Physics-based remaining range -----------------------------------
    ev_range_left = 0.0
    if usable_bat > 0:
        bat_remaining = max(0.0, usable_bat - out["battery_used_kwh"])
        ev_range_left = (bat_remaining / usable_bat) * nominal_ev_range

    fuel_range_left = 0.0
    if fuel_tank > 0:
        fuel_remaining = max(0.0, fuel_tank - out["fuel_used_l"])
        fuel_range_left = fuel_remaining * AVG_FUEL_ECONOMY_KM_PER_L

    out["range_left_km"] = round(ev_range_left + fuel_range_left, 2)

    # --- 8. Trip-time floor -------------------------------------------------
    min_time = (distance_km / MAX_SPEED_KMH) * 60.0 if distance_km > 0 else 1.0
    out["trip_time_min"] = max(out["trip_time_min"], min_time, 1.0)

    return out


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

    # ---- Apply cross-target consistency rules ------------------------------
    raw = _enforce_consistency(raw, input_data_dict)

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
