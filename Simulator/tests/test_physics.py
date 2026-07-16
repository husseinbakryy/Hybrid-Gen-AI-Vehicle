from types import SimpleNamespace

import numpy as np

from simulator.behavior import sample_behavior_state
from simulator.config import SimulationConfig
from simulator.drivers import generate_driver_profiles
from simulator.entities import TripContext, VehicleProfile
from simulator.physics import compute_baseline_trip, hybrid_switch_point_km


def _vehicle(powertrain: str) -> VehicleProfile:
    if powertrain == "ev":
        return VehicleProfile(
            vehicle_id="veh",
            make="X",
            model="Y",
            archetype="ev",
            powertrain_type="ev",
            body_type="sedan",
            battery_capacity_kwh=70,
            usable_battery_kwh=65,
            fuel_tank_l=0,
            mass_kg=1800,
            drag_coeff=0.24,
            frontal_area_m2=2.2,
            rolling_resistance_coeff=0.008,
            drivetrain_efficiency=0.91,
            regen_efficiency=0.72,
            hvac_base_kw=2.0,
            city_efficiency_factor=1.05,
            highway_efficiency_factor=0.95,
            nominal_ev_range_km=400,
            battery_health=0.92,
            vehicle_health_factor=0.95,
        )
    return VehicleProfile(
        vehicle_id="veh",
        make="X",
        model="Y",
        archetype="hybrid",
        powertrain_type="hybrid",
        body_type="sedan",
        battery_capacity_kwh=14,
        usable_battery_kwh=11,
        fuel_tank_l=45,
        mass_kg=1700,
        drag_coeff=0.25,
        frontal_area_m2=2.2,
        rolling_resistance_coeff=0.008,
        drivetrain_efficiency=0.40,
        regen_efficiency=0.68,
        hvac_base_kw=1.8,
        city_efficiency_factor=1.10,
        highway_efficiency_factor=0.98,
        nominal_ev_range_km=55,
        battery_health=0.92,
        vehicle_health_factor=0.95,
    )


def test_physics_powertrain_signals():
    rng = np.random.default_rng(5)
    driver = SimpleNamespace(**generate_driver_profiles(rng, 1).iloc[0].to_dict())
    context = TripContext(
        city="Chicago",
        season="winter",
        weather="snow",
        ambient_temp_c=-3.0,
        humidity=0.7,
        wind_speed_kmh=18.0,
        precipitation_mm=3.0,
        departure_hour=8,
        day_type="weekday",
        trip_purpose="commute",
        road_type="urban",
        traffic_level=0.74,
        expected_congestion=0.77,
        distance_km=18.0,
        elevation_gain_m=120.0,
        elevation_loss_m=80.0,
        passengers=1,
        cargo_kg=5.0,
    )
    ev = _vehicle("ev")
    hybrid = _vehicle("hybrid")
    behavior = sample_behavior_state(rng, driver, ev, context)
    config = SimulationConfig()
    ev_out = compute_baseline_trip(context, ev, behavior, config, rng)
    hy_out = compute_baseline_trip(context, hybrid, behavior, config, rng)
    assert ev_out["true_duration_min"] > 0
    assert ev_out["true_battery_used_kwh"] > 0
    assert ev_out["true_fuel_used_l"] == 0
    assert hy_out["true_battery_used_kwh"] >= 0
    assert hy_out["true_fuel_used_l"] > 0
    assert hybrid_switch_point_km(hybrid, context, behavior) > 0
