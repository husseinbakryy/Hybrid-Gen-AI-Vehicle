"""Helpers to prepare simulator output for ML training without obvious leakage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


TARGET_COLUMNS = ["recommended_mode", "estimated_cost", "estimated_time_min", "battery_used_kwh", "switch_point_km"]

LEAKAGE_PREFIXES = ("true_", "mode_score_", "mode_prob_")
LEAKAGE_COLUMNS = {
    "recommended_mode_score_margin",
    "trip_id",
    "driver_vehicle_pair_id",
    "driver_trip_index",
    "distance_km",
}

ID_COLUMNS = {"driver_id", "vehicle_id"}

OBSERVED_SENSOR_COLUMNS = {
    "observed_distance_km",
    "observed_avg_speed_kmh",
    "measured_ambient_temp_c",
    "observed_soc_pct",
    "observed_soc_start_pct",
    "observed_soc_end_pct",
    "observed_traffic_level",
    "estimated_true_duration_min_sensor",
    "estimated_true_battery_used_kwh_sensor",
    "estimated_true_fuel_used_l_sensor",
    "observed_elevation_gain_m",
    "observed_elevation_loss_m",
}

STRICT_OBSERVED_FEATURES = [
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
    "expected_congestion",
    "base_distance_km",
    "elevation_gain_m",
    "elevation_loss_m",
    "passengers",
    "cargo_kg",
    "archetype",
    "powertrain_type",
    "body_type",
    "battery_capacity_kwh",
    "usable_battery_kwh",
    "fuel_tank_l",
    "mass_kg",
    "drag_coeff",
    "frontal_area_m2",
    "rolling_resistance_coeff",
    "drivetrain_efficiency",
    "regen_efficiency",
    "hvac_base_kw",
    "city_efficiency_factor",
    "highway_efficiency_factor",
    "nominal_ev_range_km",
    "battery_health",
    "vehicle_health_factor",
    "aggressiveness",
    "consistency",
    "eco_awareness",
    "range_anxiety",
    "hvac_preference",
    "speeding_tendency",
    "braking_smoothness",
    "charging_discipline",
    "route_familiarity_bias",
    "schedule_pressure",
    "traffic_uncertainty",
]

TASK_FEATURE_SETS = {
    "recommended_mode": [
        *STRICT_OBSERVED_FEATURES,
        "observed_soc_start_pct",
    ],
    "estimated_cost": [
        *STRICT_OBSERVED_FEATURES,
        "observed_soc_start_pct",
    ],
    "estimated_time_min": [
        *STRICT_OBSERVED_FEATURES,
        "observed_soc_start_pct",
        "observed_traffic_level",
    ],
    "battery_used_kwh": [
        *STRICT_OBSERVED_FEATURES,
        "observed_soc_start_pct",
        "battery_health",
    ],
    "switch_point_km": [
        *STRICT_OBSERVED_FEATURES,
        "observed_soc_start_pct",
        "traffic_level",
        "route_familiarity_bias",
        "range_anxiety",
    ],
}


def _drop_leakage(df: pd.DataFrame) -> pd.DataFrame:
    excluded = set(TARGET_COLUMNS) | LEAKAGE_COLUMNS | ID_COLUMNS
    excluded |= {column for column in df.columns if column.startswith(LEAKAGE_PREFIXES)}
    excluded |= {column for column in df.columns if column.startswith("behavior_")}
    excluded |= {column for column in df.columns if column.startswith("true_")}
    excluded |= {column for column in df.columns if column.startswith("estimated_true_")}
    return df.drop(columns=[column for column in excluded if column in df.columns], errors="ignore")


def build_ml_views(df: pd.DataFrame) -> dict[str, Any]:
    """Return full, observed-only, feature, and target views for ML."""

    full_df = df.copy()
    observed_df = _drop_leakage(full_df)
    y = full_df[TARGET_COLUMNS].copy()

    available_features = [column for column in STRICT_OBSERVED_FEATURES if column in observed_df.columns]
    X = observed_df[available_features].copy()

    feature_sets = {
        task: [column for column in columns if column in observed_df.columns]
        for task, columns in TASK_FEATURE_SETS.items()
    }
    recommended_feature_columns = sorted({column for columns in feature_sets.values() for column in columns})

    return {
        "full_df": full_df,
        "observed_df": observed_df,
        "X": X,
        "y": y,
        "target_columns": TARGET_COLUMNS,
        "feature_sets": feature_sets,
        "recommended_feature_columns": recommended_feature_columns,
        "leakage_columns": sorted(
            set(df.columns) - set(observed_df.columns)
        ),
        "observed_sensor_columns": sorted([column for column in OBSERVED_SENSOR_COLUMNS if column in df.columns]),
    }
