from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = MODELS_DIR.parent
DEFAULT_DATA_PATH = REPO_ROOT / "Data" / "synthetic_trips.csv"
ARTIFACT_DIR = MODELS_DIR / "artifacts"

FEATURES = [
    "make",
    "model",
    "powertrain_type",
    "body_type",
    "battery_capacity_kwh",
    "usable_battery_kwh",
    "fuel_tank_l",
    "mass_kg",
    "drag_coeff",
    "frontal_area_m2",
    "city",
    "season",
    "weather",
    "ambient_temp_c",
    "humidity",
    "wind_speed_kmh",
    "precipitation_mm",
    "departure_hour",
    "day_type",
    "trip_purpose",
    "road_type",
    "traffic_level",
    "distance_km",
    "passengers",
    "cargo_kg",
]

TARGET_MAP = {
    "m1_recommended_mode": "recommended_mode",
    "m2_fuel_consumption": "true_fuel_used_l",
    "m3_battery_energy": "true_battery_used_kwh",
    "m4_co2_emissions": "true_emissions",
    "m5_trip_cost": "estimated_cost",
    "m6_range_left": "range_left_km",
    "m7_trip_time": "estimated_time_min",
}

PREPROCESSOR_FILE = "total_trip_cost_preprocessor.joblib"
MODEL_ASSETS = {
    "m1_recommended_mode": "recommended_mode_rf.joblib",
    "m2_fuel_consumption": "fuel_used_rf.joblib",
    "m3_battery_energy": "electric_used_rf.joblib",
    "m4_co2_emissions": "co2_emissions_rf.joblib",
    "m5_trip_cost": "total_trip_cost_rf.joblib",
    "m6_range_left": "range_left_rf.joblib",
    "m7_trip_time": "trip_time_rf.joblib",
}

# ---------------------------------------------------------------------------
# Domain constants for the post-prediction consistency layer
# ---------------------------------------------------------------------------
CO2_PER_LITER_FUEL = 2.31        # kg CO₂ per litre of gasoline
CO2_PER_KWH_GRID = 0.37         # kg CO₂ per kWh (grid-average electricity)
FUEL_PRICE_PER_LITER = 1.50     # USD per litre
ELEC_PRICE_PER_KWH = 0.15       # USD per kWh
EV_CONSUMPTION_KWH_PER_KM = 0.16  # kWh/km (matches Range.py assumption)
AVG_FUEL_ECONOMY_KM_PER_L = 12.0  # km per litre (average fuel economy)
MAX_SPEED_KMH = 120.0           # maximum plausible average speed
