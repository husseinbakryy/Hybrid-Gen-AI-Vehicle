"""Configuration objects and constants for the trip simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class SimulationConfig:
    """Global simulation controls and priors."""

    default_n_vehicles: int = 60
    workday_trip_share: float = 0.72
    weekend_trip_share: float = 0.28
    driver_activity_mean: float = 1.0
    driver_activity_sigma: float = 0.45
    behavior_temperature: float = 0.55
    label_temperature: float = 0.35
    observation_noise_scale: float = 0.04
    electricity_price_per_kwh: float = 0.22
    fuel_price_per_l: float = 1.35
    grid_emissions_kg_per_kwh: float = 0.37
    fuel_emissions_kg_per_l: float = 2.31
    road_speed_kmh: Dict[str, Tuple[float, float]] = field(
        default_factory=lambda: {
            "urban": (24.0, 8.0),
            "suburban": (43.0, 10.0),
            "arterial": (36.0, 9.0),
            "highway": (94.0, 16.0),
        }
    )
