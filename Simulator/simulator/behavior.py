"""Behavioral stochasticity layer."""

from __future__ import annotations

import numpy as np

from .entities import BehaviorState, DriverProfile, TripContext, VehicleProfile


def _clip(value: float, lower: float, upper: float) -> float:
    return float(np.clip(value, lower, upper))


def sample_behavior_state(
    rng: np.random.Generator,
    driver: DriverProfile,
    vehicle: VehicleProfile,
    context: TripContext,
) -> BehaviorState:
    """Convert hidden driver traits into trip-specific behavioral modifiers."""

    pressure = context.traffic_level * 0.4 + driver.schedule_pressure * 0.4 + driver.range_anxiety * 0.2
    speed_factor = _clip(1.0 + 0.10 * driver.speeding_tendency + 0.08 * driver.aggressiveness + 0.05 * pressure - 0.07 * driver.eco_awareness + rng.normal(0, 0.035), 0.82, 1.22)
    stop_go_multiplier = _clip(1.0 + 0.20 * driver.aggressiveness + 0.10 * pressure - 0.10 * driver.route_familiarity_bias + rng.normal(0, 0.05), 0.65, 1.45)
    hvac_multiplier = _clip(1.0 + 0.30 * driver.hvac_preference + 0.10 * (1.0 - driver.eco_awareness) + rng.normal(0, 0.04), 0.75, 1.60)
    regen_multiplier = _clip(1.0 + 0.16 * driver.braking_smoothness + 0.08 * driver.eco_awareness - 0.12 * driver.aggressiveness + rng.normal(0, 0.04), 0.70, 1.25)
    route_detour_factor = _clip(1.0 - 0.09 * driver.route_familiarity_bias + 0.06 * driver.traffic_uncertainty + rng.normal(0, 0.03), 0.80, 1.18)
    battery_reserve_soc = _clip(0.12 + 0.28 * driver.range_anxiety + 0.12 * driver.charging_discipline + rng.normal(0, 0.025), 0.05, 0.68)
    speed_variability = _clip(1.0 + 0.32 * (1.0 - driver.consistency) + 0.16 * driver.aggressiveness + rng.normal(0, 0.05), 0.70, 1.75)
    harsh_braking_probability = _clip(0.04 + 0.24 * driver.aggressiveness + 0.14 * pressure - 0.11 * driver.braking_smoothness + rng.normal(0, 0.02), 0.01, 0.55)
    return BehaviorState(
        speed_factor=speed_factor,
        stop_go_multiplier=stop_go_multiplier,
        hvac_multiplier=hvac_multiplier,
        regen_multiplier=regen_multiplier,
        route_detour_factor=route_detour_factor,
        battery_reserve_soc=battery_reserve_soc,
        speed_variability=speed_variability,
        harsh_braking_probability=harsh_braking_probability,
    )
