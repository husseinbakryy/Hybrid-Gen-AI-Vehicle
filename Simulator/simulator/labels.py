"""Target generation for recommendations and observed estimates."""

from __future__ import annotations

import numpy as np

from .config import SimulationConfig
from .entities import BehaviorState, DriverProfile, TripContext, VehicleProfile
from .physics import hybrid_switch_point_km


def _softmax(values: np.ndarray, temperature: float) -> np.ndarray:
    stabilized = values - np.max(values)
    exps = np.exp(stabilized / max(temperature, 1e-6))
    return exps / exps.sum()


def estimate_mode_score(
    context: TripContext,
    driver: DriverProfile,
    baseline: dict[str, float],
    vehicle: VehicleProfile,
    mode: str,
) -> float:
    estimated = _estimate_mode_outcome(context, driver, baseline, vehicle, mode)
    comfort = 1.0 - 0.22 * driver.aggressiveness + 0.18 * driver.eco_awareness - 0.08 * driver.schedule_pressure
    uncertainty = 0.25 * driver.traffic_uncertainty + 0.12 * (1.0 - driver.consistency)
    score = (
        -1.25 * estimated["cost"]
        -1.00 * estimated["time_per_km"]
        -0.28 * estimated["emissions"]
        -0.62 * estimated["battery_risk"]
        +0.55 * comfort
        -0.20 * uncertainty
    )
    score += 0.10 * estimated["mode_fit"]
    score += rng_adjustment(mode, context, driver)
    return float(score)


def rng_adjustment(mode: str, context: TripContext, driver: DriverProfile) -> float:
    if mode == "ev":
        return 0.20 * driver.eco_awareness - 0.16 * driver.range_anxiety + 0.18 * (1.0 - np.clip(context.distance_km / 90.0, 0.0, 1.0)) - 0.10 * max(0.0, 18.0 - context.ambient_temp_c) / 20.0
    if mode == "hybrid":
        return 0.10 * driver.eco_awareness + 0.14 * (1.0 - driver.range_anxiety) + 0.12 * context.traffic_level + 0.08 * (1.0 - abs(context.distance_km - 35.0) / 60.0)
    return 0.08 * driver.schedule_pressure - 0.10 * driver.eco_awareness + 0.18 * np.clip(context.distance_km / 120.0, 0.0, 1.0) + 0.10 * (context.road_type == "highway") + 0.08 * (context.trip_purpose == "road_trip")


def _estimate_mode_outcome(
    context: TripContext,
    driver: DriverProfile,
    baseline: dict[str, float],
    vehicle: VehicleProfile,
    mode: str,
) -> dict:
    distance_factor = np.clip(context.distance_km / 60.0, 0.2, 3.0)
    traffic_factor = 1.0 + 0.25 * context.traffic_level
    temp_factor = 1.0 + 0.04 * max(0.0, 18.0 - context.ambient_temp_c) / 10.0 + 0.02 * max(0.0, context.ambient_temp_c - 30.0) / 10.0
    battery_share = baseline["true_battery_used_kwh"] / max(vehicle.usable_battery_kwh, 1e-6)

    if mode == "ev":
        cost = baseline["true_energy_cost"] * (0.95 + 0.04 * temp_factor + 0.03 * traffic_factor)
        time_min = baseline["true_duration_min"] * (1.0 + 0.02 * context.traffic_level + 0.02 * (context.weather in {"snow", "heavy_rain"}))
        emissions = cost * 0.37
        battery_risk = max(0.0, battery_share - (0.55 - 0.20 * driver.range_anxiety) - 0.06 * context.ambient_temp_c / 20.0)
        mode_fit = 0.20 * driver.eco_awareness - 0.20 * driver.range_anxiety + 0.12 * (context.trip_purpose in {"commute", "errand", "business"}) - 0.08 * (context.trip_purpose == "road_trip")
    elif mode == "hybrid":
        cost = baseline["true_energy_cost"] * (0.98 + 0.02 * distance_factor + 0.02 * context.traffic_level)
        time_min = baseline["true_duration_min"] * (0.99 + 0.015 * context.traffic_level)
        emissions = baseline["true_emissions"] * (0.82 + 0.06 * context.traffic_level)
        battery_risk = max(0.0, battery_share - (0.28 - 0.08 * driver.range_anxiety))
        mode_fit = 0.10 * driver.eco_awareness + 0.14 * (1.0 - driver.range_anxiety) + 0.15 * context.traffic_level + 0.10 * (context.road_type in {"urban", "arterial"})
    else:
        cost = baseline["true_energy_cost"] * (1.04 + 0.06 * distance_factor + 0.03 * (context.road_type == "highway"))
        time_min = baseline["true_duration_min"] * (0.98 - 0.02 * (context.road_type == "highway") + 0.03 * context.traffic_level)
        emissions = baseline["true_emissions"] * (1.15 + 0.05 * distance_factor)
        battery_risk = 0.03 * driver.range_anxiety
        mode_fit = 0.08 * driver.schedule_pressure - 0.10 * driver.eco_awareness + 0.14 * (context.trip_purpose == "road_trip") + 0.08 * (context.road_type == "highway")

    return {
        "cost": float(cost),
        "time_per_km": float(time_min / max(context.distance_km, 1.0)),
        "emissions": float(emissions),
        "battery_risk": float(battery_risk),
        "mode_fit": float(mode_fit),
    }


def generate_targets(
    rng: np.random.Generator,
    context: TripContext,
    driver: DriverProfile,
    vehicle: VehicleProfile,
    behavior: BehaviorState,
    baseline: dict[str, float],
    config: SimulationConfig,
) -> dict:
    """Generate probabilistic labels and observed estimates."""

    mode_candidates = ["ev", "hybrid", "ice"]
    mode_outcomes = [_estimate_mode_outcome(context, driver, baseline, vehicle, mode) for mode in mode_candidates]
    scores = np.array([estimate_mode_score(context, driver, baseline, vehicle, mode) for mode in mode_candidates], dtype=float)
    probabilities = _softmax(scores, config.label_temperature)
    ranked = np.argsort(scores)
    top_index = int(ranked[-1])
    runner_up_index = int(ranked[-2])
    recommended_mode = str(mode_candidates[top_index])
    if scores[top_index] - scores[runner_up_index] < 0.35:
        recommended_mode = str(rng.choice([mode_candidates[top_index], mode_candidates[runner_up_index]], p=[0.58, 0.42]))
    elif rng.random() < 0.15:
        recommended_mode = str(rng.choice(mode_candidates, p=probabilities))
    sorted_scores = np.sort(scores)
    score_margin = float(sorted_scores[-1] - sorted_scores[-2])
    chosen_outcome = mode_outcomes[top_index]
    estimated_cost = max(0.0, chosen_outcome["cost"] * rng.normal(1.02, 0.05) + rng.normal(0.0, 0.12))
    estimated_time = max(1.0, chosen_outcome["time_per_km"] * context.distance_km * rng.normal(1.01, 0.04) + rng.normal(0.0, 0.9))
    estimated_battery_used_kwh = max(0.0, baseline["true_battery_used_kwh"] * rng.normal(1.00, 0.05) + rng.normal(0.0, 0.08))
    switch_point_km = hybrid_switch_point_km(vehicle, context, behavior)

    return {
        "mode_score_ev": float(scores[0]),
        "mode_score_hybrid": float(scores[1]),
        "mode_score_ice": float(scores[2]),
        "mode_prob_ev": float(probabilities[0]),
        "mode_prob_hybrid": float(probabilities[1]),
        "mode_prob_ice": float(probabilities[2]),
        "recommended_mode": recommended_mode,
        "recommended_mode_score_margin": score_margin,
        "estimated_cost": float(estimated_cost),
        "estimated_time_min": float(estimated_time),
        "battery_used_kwh": float(estimated_battery_used_kwh),
        "switch_point_km": float(switch_point_km),
    }
