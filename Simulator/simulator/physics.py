"""Physics-inspired baseline for trip duration and energy use."""

from __future__ import annotations

import numpy as np

from .config import SimulationConfig
from .entities import BehaviorState, TripContext, VehicleProfile


def _clip(value: float, lower: float, upper: float) -> float:
    return float(np.clip(value, lower, upper))


def _road_speed_factor(road_type: str) -> float:
    return {"urban": 0.62, "arterial": 0.80, "suburban": 0.92, "highway": 1.08}[road_type]


def _traffic_speed_penalty(traffic_level: float) -> float:
    return 1.0 - 0.30 * traffic_level


def _weather_speed_penalty(context: TripContext) -> float:
    penalty = 1.0
    if context.precipitation_mm > 0.0:
        penalty -= 0.04 + min(0.08, context.precipitation_mm / 80.0)
    if context.ambient_temp_c < 0.0 or context.ambient_temp_c > 33.0:
        penalty -= 0.03
    if context.wind_speed_kmh > 20.0:
        penalty -= 0.02
    return max(0.82, penalty)


def _hvac_load_kw(vehicle: VehicleProfile, context: TripContext, behavior: BehaviorState) -> float:
    temp_gap = abs(context.ambient_temp_c - 21.0)
    humidity_term = 0.15 + 0.6 * context.humidity
    weather_term = 0.14 if context.precipitation_mm > 0.0 else 0.0
    return vehicle.hvac_base_kw * behavior.hvac_multiplier * (1.0 + 0.028 * temp_gap + 0.16 * humidity_term + weather_term)


def context_and_grid_factor(context: TripContext, config: SimulationConfig) -> float:
    return config.grid_emissions_kg_per_kwh


def compute_baseline_trip(
    context: TripContext,
    vehicle: VehicleProfile,
    behavior: BehaviorState,
    config: SimulationConfig,
    rng: np.random.Generator,
) -> dict:
    """Compute trip outcome before measurement noise."""

    mass_kg = vehicle.mass_kg + context.passengers * 72.0 + context.cargo_kg
    road_factor = _road_speed_factor(context.road_type)
    traffic_factor = _traffic_speed_penalty(context.traffic_level)
    weather_factor = _weather_speed_penalty(context)
    speed_noise = float(np.clip(rng.normal(1.0, 0.04 * behavior.speed_variability), 0.78, 1.28))
    true_avg_speed_kmh = _clip(road_factor * traffic_factor * weather_factor * behavior.speed_factor * speed_noise * 96.0, 9.0, 121.0)

    base_duration_hr = context.distance_km / true_avg_speed_kmh
    stop_count = max(0.0, context.distance_km * (0.16 if context.road_type == "urban" else 0.07) * (0.65 + 0.90 * context.traffic_level))
    stop_count *= behavior.stop_go_multiplier * (1.0 + 0.08 * (1.0 - behavior.route_detour_factor))
    stop_penalty_min = stop_count * (0.55 + 1.35 * behavior.harsh_braking_probability)
    grade_penalty_min = 0.014 * context.elevation_gain_m / max(1.0, true_avg_speed_kmh / 20.0)
    duration_noise_min = rng.normal(0.0, max(1.0, 0.04 * context.distance_km + 0.02 * stop_count))
    true_duration_min = max(3.0, base_duration_hr * 60.0 + stop_penalty_min + grade_penalty_min + duration_noise_min)

    speed_mps = true_avg_speed_kmh / 3.6
    distance_m = context.distance_km * 1000.0 * behavior.route_detour_factor
    tire_factor = 1.0 + 0.12 * (1.0 - vehicle.vehicle_health_factor)
    rolling_force = vehicle.rolling_resistance_coeff * tire_factor * mass_kg * 9.81
    aero_force = 0.5 * 1.225 * vehicle.drag_coeff * vehicle.frontal_area_m2 * speed_mps**2
    grade_force = 9.81 * mass_kg * ((context.elevation_gain_m - 0.45 * context.elevation_loss_m) / max(distance_m, 1.0))
    acceleration_penalty = mass_kg * 0.00022 * stop_count * (1.0 + 0.55 * behavior.harsh_braking_probability + 0.25 * (1.0 - vehicle.vehicle_health_factor))
    base_mech_energy_kwh = max(0.0, (rolling_force + aero_force + max(0.0, grade_force)) * distance_m / 3.6e6)
    stop_go_energy_kwh = acceleration_penalty / 1000.0
    hvac_kw = _hvac_load_kw(vehicle, context, behavior)
    hvac_energy_kwh = hvac_kw * true_duration_min / 60.0
    temp_penalty = 1.0 + 0.018 * max(0.0, 18.0 - context.ambient_temp_c) + 0.010 * max(0.0, context.ambient_temp_c - 29.0)
    humidity_penalty = 1.0 + 0.008 * max(0.0, context.humidity - 0.65)
    weather_energy_multiplier = temp_penalty * humidity_penalty * (1.0 + 0.01 * context.wind_speed_kmh / 10.0)
    total_propulsion_kwh = (base_mech_energy_kwh + stop_go_energy_kwh) * weather_energy_multiplier
    total_energy_kwh = total_propulsion_kwh + hvac_energy_kwh

    temp_battery_degradation = 1.0 + 0.18 * max(0.0, 12.0 - context.ambient_temp_c) / 20.0 + 0.10 * max(0.0, context.ambient_temp_c - 30.0) / 18.0
    battery_health_penalty = 1.0 + 0.20 * (1.0 - vehicle.battery_health)
    ev_efficiency = vehicle.drivetrain_efficiency * battery_health_penalty * temp_battery_degradation
    ev_efficiency *= vehicle.city_efficiency_factor if context.road_type in {"urban", "arterial"} else vehicle.highway_efficiency_factor
    if vehicle.powertrain_type == "ev":
        regen_credit = min(total_propulsion_kwh * 0.18, total_propulsion_kwh * vehicle.regen_efficiency * behavior.regen_multiplier * 0.22)
        true_battery_used_kwh = max(0.0, total_energy_kwh / max(0.55, ev_efficiency) - regen_credit)
        true_fuel_used_l = 0.0
    elif vehicle.powertrain_type == "ice":
        thermal_efficiency = max(0.20, vehicle.drivetrain_efficiency)
        true_fuel_used_l = total_energy_kwh / (8.9 * thermal_efficiency)
        true_battery_used_kwh = 0.0
    else:
        city_share = 0.58 if context.road_type in {"urban", "arterial"} else 0.32
        eco_shift = 0.10 * behavior.regen_multiplier + 0.08 * (1.0 - behavior.battery_reserve_soc) + 0.08 * (1.0 if context.distance_km < 28.0 else 0.0)
        electric_share = _clip(city_share + eco_shift - 0.12 * behavior.speed_factor + 0.06 * (1.0 - context.traffic_level), 0.18, 0.72)
        electric_kwh = total_energy_kwh * electric_share / max(0.55, ev_efficiency)
        regen_credit = min(electric_kwh * 0.12, electric_kwh * vehicle.regen_efficiency * behavior.regen_multiplier * 0.16)
        true_battery_used_kwh = max(0.0, electric_kwh - regen_credit)
        fuel_kwh_equiv = total_energy_kwh * (1.0 - electric_share)
        true_fuel_used_l = fuel_kwh_equiv / (8.9 * max(0.22, vehicle.drivetrain_efficiency))

    true_energy_cost = true_battery_used_kwh * config.electricity_price_per_kwh + true_fuel_used_l * config.fuel_price_per_l
    true_emissions = true_battery_used_kwh * context_and_grid_factor(context, config) + true_fuel_used_l * config.fuel_emissions_kg_per_l
    return {
        "true_duration_min": float(true_duration_min),
        "true_avg_speed_kmh": float(true_avg_speed_kmh),
        "true_battery_used_kwh": float(true_battery_used_kwh),
        "true_fuel_used_l": float(true_fuel_used_l),
        "true_energy_cost": float(true_energy_cost),
        "true_emissions": float(true_emissions),
        "true_stop_count": float(stop_count),
        "true_hvac_kw": float(hvac_kw),
        "true_total_energy_kwh": float(total_energy_kwh),
        "true_propulsion_energy_kwh": float(total_propulsion_kwh),
        "mass_kg_effective": float(mass_kg),
    }


def hybrid_switch_point_km(vehicle: VehicleProfile, context: TripContext, behavior: BehaviorState) -> float:
    """Approximate the distance at which hybrid operation becomes dominant."""

    if vehicle.powertrain_type != "hybrid":
        return float("nan")
    road_pressure = 1.0 + 0.20 * (context.road_type in {"urban", "arterial"}) - 0.10 * (context.road_type == "highway")
    traffic_pressure = 1.0 + 0.32 * context.traffic_level + 0.08 * context.expected_congestion
    battery_pressure = 1.0 + 0.28 * (1.0 - behavior.battery_reserve_soc) + 0.10 * (1.0 - vehicle.battery_health)
    weather_pressure = 1.0 + 0.08 * (context.ambient_temp_c < 0.0) + 0.05 * (context.precipitation_mm > 0.0)
    base = 10.0 + 0.18 * vehicle.usable_battery_kwh + 4.5 * context.traffic_level + 0.12 * context.distance_km
    base *= road_pressure * traffic_pressure * battery_pressure * weather_pressure
    base *= 1.0 + 0.12 * (context.trip_purpose == "road_trip") - 0.08 * behavior.speed_factor
    if context.road_type in {"urban", "arterial"}:
        base *= 0.88
    else:
        base *= 1.18
    return float(np.clip(base, 5.0, max(35.0, context.distance_km * 1.15)))
