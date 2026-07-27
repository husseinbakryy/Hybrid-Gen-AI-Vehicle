"""Per-tick physics adapter for real-time trip simulation.

Translates the full-trip physics engine from the Simulator into
granular, per-second computations suitable for real-time streaming.
Each ``tick`` represents one simulated second of driving.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Domain constants (aligned with Simulator and ML pipeline config)
# ---------------------------------------------------------------------------

AIR_DENSITY_KG_M3 = 1.225
GRAVITY_MPS2 = 9.81

# Pricing / emissions (matches Models/pipeline/config.py)
FUEL_PRICE_PER_L = 1.50
ELEC_PRICE_PER_KWH = 0.15
CO2_PER_LITER_FUEL = 2.31
CO2_PER_KWH_GRID = 0.37
EV_CONSUMPTION_KWH_PER_KM = 0.16

# Acceleration / deceleration rate limits (m/s²)
MAX_ACCEL_MPS2 = 3.0        # comfortable gas-pedal acceleration
MAX_DECEL_MPS2 = -5.0       # moderate braking deceleration
COAST_DECEL_MPS2 = -0.3     # gentle drag deceleration when coasting

# Gas pedal acceleration - intentionally a separate constant from
# MAX_ACCEL_MPS2 (which also feeds the coast-branch clamp bound),
# so tuning this can never affect coasting or braking behavior.
GAS_PEDAL_ACCEL_MPS2 = 3.6   # ~20% brisker than the old 3.0 baseline

# Speed bounds (km/h)
MIN_SPEED_KMH = 0.0
MAX_SPEED_KMH = 180.0

# Road-type base speed targets (km/h) for coast / natural speed
ROAD_BASE_SPEED_KMH: dict[str, float] = {
    "urban": 35.0,
    "suburban": 55.0,
    "arterial": 45.0,
    "highway": 100.0,
}

# ICE thermal efficiency for fuel → mechanical kWh conversion
ICE_ENERGY_CONTENT_KWH_PER_L = 8.9  # approximate energy per litre gasoline


# ---------------------------------------------------------------------------
# Vehicle spec helper — builds a lightweight dict from DB vehicle doc
# ---------------------------------------------------------------------------

@dataclass
class VehicleSpec:
    """Lightweight vehicle specification for tick physics."""

    mass_kg: float
    drag_coeff: float
    frontal_area_m2: float
    rolling_resistance_coeff: float
    drivetrain_efficiency: float
    regen_efficiency: float
    usable_battery_kwh: float
    fuel_tank_l: float
    powertrain_type: str  # "ev", "hybrid", "ice"
    battery_health: float = 1.0
    vehicle_health_factor: float = 1.0


def vehicle_spec_from_db(vehicle_doc: dict[str, Any]) -> VehicleSpec:
    """Build a VehicleSpec from a database vehicle document."""
    specs = vehicle_doc.get("specifications", {})
    return VehicleSpec(
        mass_kg=float(specs.get("massKg", 1500.0)),
        drag_coeff=float(specs.get("dragCoeff", 0.28)),
        frontal_area_m2=float(specs.get("frontalAreaM2", 2.3)),
        rolling_resistance_coeff=float(specs.get("rollingResistanceCoeff", 0.008)),
        drivetrain_efficiency=float(specs.get("drivetrainEfficiency", 0.35)),
        regen_efficiency=float(specs.get("regenEfficiency", 0.70)),
        usable_battery_kwh=float(specs.get("usableBatteryKwh", 0.0)),
        fuel_tank_l=float(specs.get("fuelTankL", 0.0)),
        powertrain_type=(specs.get("powertrainType") or vehicle_doc.get("powertrain_type", "hybrid")).lower(),
        battery_health=float(specs.get("batteryHealth", 1.0)),
        vehicle_health_factor=float(specs.get("vehicleHealthFactor", 1.0)),
    )


# ---------------------------------------------------------------------------
# Core per-tick computations
# ---------------------------------------------------------------------------

def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def compute_speed_change(
    current_speed_kmh: float,
    action: str,
    road_type: str,
    traffic_level: float,
    dt_seconds: float,
) -> tuple[float, float]:
    """Compute the new speed and acceleration for one tick."""
    current_speed_mps = current_speed_kmh / 3.6

    if action == "accelerate":
        speed_factor = max(0.2, 1.0 - (current_speed_kmh / MAX_SPEED_KMH))
        traffic_penalty = 1.0 - 0.4 * traffic_level
        accel = GAS_PEDAL_ACCEL_MPS2 * speed_factor * traffic_penalty
    elif action == "brake":
        accel = MAX_DECEL_MPS2 * (0.6 + 0.4 * min(1.0, current_speed_kmh / 60.0))
    else:
        base_speed = ROAD_BASE_SPEED_KMH.get(road_type, 45.0) * (1.0 - 0.3 * traffic_level)
        speed_diff_kmh = base_speed - current_speed_kmh
        accel = _clamp(speed_diff_kmh / 3.6 * 0.15, COAST_DECEL_MPS2, MAX_ACCEL_MPS2 * 0.3)

    new_speed_mps = current_speed_mps + accel * dt_seconds
    new_speed_kmh = _clamp(new_speed_mps * 3.6, MIN_SPEED_KMH, MAX_SPEED_KMH)

    actual_accel = (new_speed_kmh / 3.6 - current_speed_mps) / max(dt_seconds, 0.001)

    return new_speed_kmh, actual_accel


def compute_regen_energy(
    speed_before_kmh: float,
    speed_after_kmh: float,
    vehicle: VehicleSpec,
    passengers: int = 1,
    cargo_kg: float = 0.0,
) -> float:
    """Compute regenerative braking energy recovered (kWh)."""
    if vehicle.powertrain_type == "ice":
        return 0.0

    if speed_after_kmh >= speed_before_kmh:
        return 0.0

    total_mass = vehicle.mass_kg + passengers * 72.0 + cargo_kg

    v_before_mps = speed_before_kmh / 3.6
    v_after_mps = speed_after_kmh / 3.6

    ke_diff_j = 0.5 * total_mass * (v_before_mps ** 2 - v_after_mps ** 2)
    ke_diff_kwh = ke_diff_j / 3_600_000.0
    regen_kwh = ke_diff_kwh * vehicle.regen_efficiency * vehicle.battery_health

    return max(0.0, regen_kwh)


def compute_tick_energy(
    avg_speed_kmh: float,
    acceleration_mps2: float,
    vehicle: VehicleSpec,
    current_mode: str,
    dt_seconds: float,
    passengers: int = 1,
    cargo_kg: float = 0.0,
    ambient_temp_c: float = 20.0,
    wind_speed_kmh: float = 0.0,
) -> dict[str, float]:
    """Compute energy consumed in one tick."""
    speed_mps = avg_speed_kmh / 3.6
    distance_m = speed_mps * dt_seconds
    distance_km = distance_m / 1000.0

    total_mass = vehicle.mass_kg + passengers * 72.0 + cargo_kg

    tire_factor = 1.0 + 0.12 * (1.0 - vehicle.vehicle_health_factor)
    rolling_force = vehicle.rolling_resistance_coeff * tire_factor * total_mass * GRAVITY_MPS2
    aero_force = 0.5 * AIR_DENSITY_KG_M3 * vehicle.drag_coeff * vehicle.frontal_area_m2 * speed_mps ** 2

    wind_mps = wind_speed_kmh / 3.6
    effective_aero = 0.5 * AIR_DENSITY_KG_M3 * vehicle.drag_coeff * vehicle.frontal_area_m2 * (speed_mps + wind_mps * 0.3) ** 2
    aero_force = max(aero_force, effective_aero)

    accel_force = max(0.0, total_mass * acceleration_mps2)
    total_force = rolling_force + aero_force + accel_force
    mechanical_energy_kwh = max(0.0, total_force * distance_m / 3_600_000.0)

    temp_gap = abs(ambient_temp_c - 21.0)
    hvac_kw = 1.8 * (1.0 + 0.028 * temp_gap)
    hvac_energy_kwh = hvac_kw * dt_seconds / 3600.0

    total_energy_kwh = mechanical_energy_kwh + hvac_energy_kwh

    battery_used = 0.0
    fuel_used = 0.0
    mode = current_mode.lower()

    if mode == "ev":
        eff = max(0.55, vehicle.drivetrain_efficiency * (1.0 + 0.2 * (1.0 - vehicle.battery_health)))
        battery_used = total_energy_kwh / eff
        fuel_used = 0.0
    elif mode == "ice":
        thermal_eff = max(0.20, vehicle.drivetrain_efficiency)
        fuel_used = total_energy_kwh / (ICE_ENERGY_CONTENT_KWH_PER_L * thermal_eff)
        battery_used = 0.0
    else:
        ev_share = _clamp(0.65 - 0.005 * avg_speed_kmh, 0.2, 0.7)
        eff = max(0.55, vehicle.drivetrain_efficiency * (1.0 + 0.2 * (1.0 - vehicle.battery_health)))
        battery_used = (total_energy_kwh * ev_share) / eff
        thermal_eff = max(0.20, vehicle.drivetrain_efficiency)
        fuel_used = (total_energy_kwh * (1.0 - ev_share)) / (ICE_ENERGY_CONTENT_KWH_PER_L * thermal_eff)

    co2_kg = fuel_used * CO2_PER_LITER_FUEL + battery_used * CO2_PER_KWH_GRID
    cost_usd = fuel_used * FUEL_PRICE_PER_L + battery_used * ELEC_PRICE_PER_KWH

    return {
        "battery_used_kwh": max(0.0, battery_used),
        "fuel_used_l": max(0.0, fuel_used),
        "co2_kg": max(0.0, co2_kg),
        "cost_usd": max(0.0, cost_usd),
        "distance_km": max(0.0, distance_km),
    }


def compute_range_left(
    battery_soc_pct: float,
    fuel_level_pct: float,
    vehicle: VehicleSpec,
) -> float:
    """Estimate remaining range (km) from current battery and fuel levels."""
    ev_range = 0.0
    if vehicle.usable_battery_kwh > 0 and vehicle.powertrain_type != "ice":
        remaining_kwh = vehicle.usable_battery_kwh * (battery_soc_pct / 100.0)
        ev_range = remaining_kwh / EV_CONSUMPTION_KWH_PER_KM

    fuel_range = 0.0
    if vehicle.fuel_tank_l > 0 and vehicle.powertrain_type != "ev":
        remaining_l = vehicle.fuel_tank_l * (fuel_level_pct / 100.0)
        fuel_range = remaining_l * 12.0

    return ev_range + fuel_range
