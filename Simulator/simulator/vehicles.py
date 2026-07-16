"""Vehicle fleet generation."""

from __future__ import annotations

import numpy as np
import pandas as pd


_ARCHETYPES = [
    {
        "archetype": "ev_hatchback",
        "make": "Nexa",
        "model": "VoltMini",
        "powertrain_type": "ev",
        "body_type": "hatchback",
        "battery_capacity_kwh": 52.0,
        "usable_battery_kwh": 48.0,
        "fuel_tank_l": 0.0,
        "mass_kg": 1620.0,
        "drag_coeff": 0.27,
        "frontal_area_m2": 2.22,
        "rolling_resistance_coeff": 0.0082,
        "drivetrain_efficiency": 0.90,
        "regen_efficiency": 0.72,
        "hvac_base_kw": 1.8,
        "city_efficiency_factor": 1.08,
        "highway_efficiency_factor": 0.92,
        "nominal_ev_range_km": 330.0,
    },
    {
        "archetype": "ev_sedan",
        "make": "Aster",
        "model": "Luma 5",
        "powertrain_type": "ev",
        "body_type": "sedan",
        "battery_capacity_kwh": 74.0,
        "usable_battery_kwh": 69.0,
        "fuel_tank_l": 0.0,
        "mass_kg": 1880.0,
        "drag_coeff": 0.23,
        "frontal_area_m2": 2.28,
        "rolling_resistance_coeff": 0.0080,
        "drivetrain_efficiency": 0.92,
        "regen_efficiency": 0.75,
        "hvac_base_kw": 2.0,
        "city_efficiency_factor": 1.05,
        "highway_efficiency_factor": 0.95,
        "nominal_ev_range_km": 440.0,
    },
    {
        "archetype": "hybrid_sedan",
        "make": "Orion",
        "model": "Pulse H",
        "powertrain_type": "hybrid",
        "body_type": "sedan",
        "battery_capacity_kwh": 13.8,
        "usable_battery_kwh": 10.5,
        "fuel_tank_l": 43.0,
        "mass_kg": 1625.0,
        "drag_coeff": 0.24,
        "frontal_area_m2": 2.25,
        "rolling_resistance_coeff": 0.0078,
        "drivetrain_efficiency": 0.41,
        "regen_efficiency": 0.68,
        "hvac_base_kw": 1.6,
        "city_efficiency_factor": 1.15,
        "highway_efficiency_factor": 0.98,
        "nominal_ev_range_km": 58.0,
    },
    {
        "archetype": "hybrid_suv",
        "make": "Terra",
        "model": "Trail H",
        "powertrain_type": "hybrid",
        "body_type": "suv",
        "battery_capacity_kwh": 16.2,
        "usable_battery_kwh": 12.1,
        "fuel_tank_l": 51.0,
        "mass_kg": 2010.0,
        "drag_coeff": 0.31,
        "frontal_area_m2": 2.55,
        "rolling_resistance_coeff": 0.0086,
        "drivetrain_efficiency": 0.38,
        "regen_efficiency": 0.64,
        "hvac_base_kw": 2.1,
        "city_efficiency_factor": 1.10,
        "highway_efficiency_factor": 0.96,
        "nominal_ev_range_km": 51.0,
    },
    {
        "archetype": "ice_sedan",
        "make": "Helio",
        "model": "Cruze L",
        "powertrain_type": "ice",
        "body_type": "sedan",
        "battery_capacity_kwh": 0.9,
        "usable_battery_kwh": 0.4,
        "fuel_tank_l": 50.0,
        "mass_kg": 1460.0,
        "drag_coeff": 0.26,
        "frontal_area_m2": 2.18,
        "rolling_resistance_coeff": 0.0085,
        "drivetrain_efficiency": 0.29,
        "regen_efficiency": 0.18,
        "hvac_base_kw": 1.7,
        "city_efficiency_factor": 0.92,
        "highway_efficiency_factor": 1.04,
        "nominal_ev_range_km": 0.0,
    },
    {
        "archetype": "ice_suv",
        "make": "Helio",
        "model": "Rover X",
        "powertrain_type": "ice",
        "body_type": "suv",
        "battery_capacity_kwh": 1.0,
        "usable_battery_kwh": 0.5,
        "fuel_tank_l": 62.0,
        "mass_kg": 2240.0,
        "drag_coeff": 0.34,
        "frontal_area_m2": 2.66,
        "rolling_resistance_coeff": 0.0091,
        "drivetrain_efficiency": 0.25,
        "regen_efficiency": 0.12,
        "hvac_base_kw": 2.2,
        "city_efficiency_factor": 0.88,
        "highway_efficiency_factor": 1.05,
        "nominal_ev_range_km": 0.0,
    },
]


def _bounded_noise(rng: np.random.Generator, value: float, scale: float, lower: float, upper: float) -> float:
    return float(np.clip(value + rng.normal(0.0, scale), lower, upper))


def generate_vehicle_fleet(rng: np.random.Generator, n_vehicles: int) -> pd.DataFrame:
    """Generate a persistent fleet of vehicles with mild within-archetype variation."""

    rows: list[dict] = []
    for index in range(n_vehicles):
        archetype = dict(_ARCHETYPES[index % len(_ARCHETYPES)])
        archetype_name = archetype.pop("archetype")
        rows.append(
            {
                "vehicle_id": f"veh_{index:04d}",
                "archetype": archetype_name,
                "make": archetype["make"],
                "model": archetype["model"],
                "powertrain_type": archetype["powertrain_type"],
                "body_type": archetype["body_type"],
                "battery_capacity_kwh": _bounded_noise(rng, archetype["battery_capacity_kwh"], 1.8, 0.0, 120.0),
                "usable_battery_kwh": _bounded_noise(rng, archetype["usable_battery_kwh"], 1.5, 0.0, 120.0),
                "fuel_tank_l": _bounded_noise(rng, archetype["fuel_tank_l"], 2.0, 0.0, 90.0),
                "mass_kg": _bounded_noise(rng, archetype["mass_kg"], 70.0, 1000.0, 3200.0),
                "drag_coeff": _bounded_noise(rng, archetype["drag_coeff"], 0.015, 0.18, 0.42),
                "frontal_area_m2": _bounded_noise(rng, archetype["frontal_area_m2"], 0.10, 1.8, 3.1),
                "rolling_resistance_coeff": _bounded_noise(rng, archetype["rolling_resistance_coeff"], 0.0004, 0.006, 0.012),
                "drivetrain_efficiency": _bounded_noise(rng, archetype["drivetrain_efficiency"], 0.02, 0.18, 0.96),
                "regen_efficiency": _bounded_noise(rng, archetype["regen_efficiency"], 0.03, 0.0, 0.90),
                "hvac_base_kw": _bounded_noise(rng, archetype["hvac_base_kw"], 0.18, 0.8, 3.4),
                "city_efficiency_factor": _bounded_noise(rng, archetype["city_efficiency_factor"], 0.04, 0.75, 1.25),
                "highway_efficiency_factor": _bounded_noise(rng, archetype["highway_efficiency_factor"], 0.04, 0.75, 1.25),
                "nominal_ev_range_km": _bounded_noise(rng, archetype["nominal_ev_range_km"], 18.0, 0.0, 800.0),
                "battery_health": float(np.clip(rng.beta(18, 3), 0.35, 1.0)),
                "vehicle_health_factor": float(np.clip(rng.beta(20, 2.5), 0.30, 1.0)),
            }
        )
    return pd.DataFrame(rows)
