"""Measurement noise and observed-variable generation."""

from __future__ import annotations

import numpy as np

from .config import SimulationConfig


def _noisy(rng: np.random.Generator, value: float, relative: float, absolute: float = 0.0) -> float:
    scale = max(absolute, abs(value) * relative)
    return float(value + rng.normal(0.0, scale))


def apply_measurement_noise(
    rng: np.random.Generator,
    base_record: dict,
    config: SimulationConfig,
) -> dict:
    """Generate observed fields with realistic sensor and estimation noise."""

    observed = dict(base_record)
    observed["observed_distance_km"] = max(0.1, _noisy(rng, base_record["distance_km"], 0.01, 0.03))
    observed["observed_avg_speed_kmh"] = max(1.0, _noisy(rng, base_record["true_avg_speed_kmh"], 0.03, 0.4))
    observed["measured_ambient_temp_c"] = _noisy(rng, base_record["ambient_temp_c"], 0.012, 0.12)
    observed["observed_soc_start_pct"] = float(np.clip(_noisy(rng, base_record.get("true_battery_soc_start_pct", base_record.get("soc_pct", 0.62)), 0.035, 0.8), 0.0, 100.0))
    observed["observed_soc_end_pct"] = float(np.clip(_noisy(rng, base_record.get("true_battery_soc_end_pct", base_record.get("soc_pct", 0.62)), 0.035, 0.8), 0.0, 100.0))
    observed["observed_soc_pct"] = observed["observed_soc_start_pct"]
    observed["observed_traffic_level"] = float(np.clip(_noisy(rng, base_record["traffic_level"], 0.08, 0.02), 0.0, 1.0))
    observed["estimated_true_duration_min_sensor"] = max(1.0, _noisy(rng, base_record["true_duration_min"], 0.04, 0.8))
    observed["estimated_true_battery_used_kwh_sensor"] = max(0.0, _noisy(rng, base_record["true_battery_used_kwh"], 0.06, 0.03))
    observed["estimated_true_fuel_used_l_sensor"] = max(0.0, _noisy(rng, base_record["true_fuel_used_l"], 0.06, 0.02))
    observed["observed_elevation_gain_m"] = max(0.0, _noisy(rng, base_record["elevation_gain_m"], 0.05, 2.0))
    observed["observed_elevation_loss_m"] = max(0.0, _noisy(rng, base_record["elevation_loss_m"], 0.05, 2.0))
    return observed
