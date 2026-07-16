"""Driver profile generation with correlated latent behavior variables."""

from __future__ import annotations

import numpy as np
import pandas as pd


PURPOSES = ["commute", "errand", "school_run", "leisure", "airport", "road_trip", "business"]


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _clip01(values: np.ndarray) -> np.ndarray:
    return np.clip(values, 0.0, 1.0)


def generate_driver_profiles(rng: np.random.Generator, n_drivers: int) -> pd.DataFrame:
    """Generate persistent driver entities with correlated hidden traits."""

    latent = rng.multivariate_normal(
        mean=np.zeros(5),
        cov=np.array(
            [
                [1.0, 0.25, -0.15, 0.20, 0.10],
                [0.25, 1.0, -0.20, 0.15, 0.15],
                [-0.15, -0.20, 1.0, -0.05, 0.05],
                [0.20, 0.15, -0.05, 1.0, 0.20],
                [0.10, 0.15, 0.05, 0.20, 1.0],
            ]
        ),
        size=n_drivers,
    )
    risk = _sigmoid(latent[:, 0])
    discipline = _sigmoid(latent[:, 1])
    eco = _sigmoid(latent[:, 2])
    stress = _sigmoid(latent[:, 3])
    locality = _sigmoid(latent[:, 4])

    rows: list[dict] = []
    for index in range(n_drivers):
        aggressiveness = float(_clip01(0.55 * risk[index] + 0.2 * stress[index] + rng.normal(0, 0.06)))
        consistency = float(_clip01(0.68 * discipline[index] + 0.12 * eco[index] + rng.normal(0, 0.05)))
        eco_awareness = float(_clip01(0.75 * eco[index] + 0.12 * discipline[index] + rng.normal(0, 0.05)))
        range_anxiety = float(_clip01(0.55 * stress[index] + 0.18 * (1.0 - eco_awareness) + rng.normal(0, 0.06)))
        hvac_preference = float(_clip01(0.46 + 0.28 * stress[index] + 0.18 * (1.0 - eco_awareness) + rng.normal(0, 0.05)))
        speeding_tendency = float(_clip01(0.6 * risk[index] + 0.18 * stress[index] + rng.normal(0, 0.06)))
        braking_smoothness = float(_clip01(0.72 * discipline[index] - 0.16 * aggressiveness + rng.normal(0, 0.05)))
        charging_discipline = float(_clip01(0.7 * discipline[index] + 0.12 * eco_awareness + rng.normal(0, 0.05)))
        route_familiarity_bias = float(_clip01(0.62 * locality[index] + 0.15 * discipline[index] + rng.normal(0, 0.05)))
        schedule_pressure = float(_clip01(0.52 * stress[index] + 0.26 * risk[index] + rng.normal(0, 0.05)))
        traffic_uncertainty = float(_clip01(0.44 * stress[index] + 0.22 * risk[index] + rng.normal(0, 0.06)))
        vehicle_health_factor = float(_clip01(0.74 * discipline[index] + 0.12 * eco_awareness + rng.normal(0, 0.05)))
        battery_health = float(_clip01(0.8 * vehicle_health_factor + 0.1 * charging_discipline + rng.normal(0, 0.05)))
        tire_condition = float(_clip01(0.78 * vehicle_health_factor + 0.08 * discipline[index] + rng.normal(0, 0.05)))
        preferred_trip_purposes = list(
            rng.choice(PURPOSES, size=int(rng.integers(2, 5)), replace=False, p=np.array([0.24, 0.15, 0.12, 0.16, 0.10, 0.10, 0.13]))
        )
        rows.append(
            {
                "driver_id": f"drv_{index:04d}",
                "aggressiveness": aggressiveness,
                "consistency": consistency,
                "eco_awareness": eco_awareness,
                "range_anxiety": range_anxiety,
                "hvac_preference": hvac_preference,
                "speeding_tendency": speeding_tendency,
                "braking_smoothness": braking_smoothness,
                "charging_discipline": charging_discipline,
                "route_familiarity_bias": route_familiarity_bias,
                "preferred_trip_purposes": preferred_trip_purposes,
                "schedule_pressure": schedule_pressure,
                "traffic_uncertainty": traffic_uncertainty,
                "vehicle_health_factor": vehicle_health_factor,
                "battery_health": battery_health,
                "tire_condition": tire_condition,
            }
        )
    return pd.DataFrame(rows)
