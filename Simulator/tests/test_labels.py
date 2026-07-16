from types import SimpleNamespace

import numpy as np

from simulator.behavior import sample_behavior_state
from simulator.config import SimulationConfig
from simulator.drivers import generate_driver_profiles
from simulator.entities import TripContext, VehicleProfile
from simulator.labels import generate_targets
from simulator.physics import compute_baseline_trip


def _vehicle() -> VehicleProfile:
    return VehicleProfile(
        vehicle_id="veh",
        make="X",
        model="Y",
        archetype="hybrid",
        powertrain_type="hybrid",
        body_type="suv",
        battery_capacity_kwh=16,
        usable_battery_kwh=12,
        fuel_tank_l=50,
        mass_kg=2000,
        drag_coeff=0.31,
        frontal_area_m2=2.5,
        rolling_resistance_coeff=0.0084,
        drivetrain_efficiency=0.39,
        regen_efficiency=0.66,
        hvac_base_kw=2.0,
        city_efficiency_factor=1.1,
        highway_efficiency_factor=0.97,
        nominal_ev_range_km=52,
        battery_health=0.9,
        vehicle_health_factor=0.94,
    )


def test_targets_are_probabilistic_and_noisy():
    rng = np.random.default_rng(11)
    driver = SimpleNamespace(**generate_driver_profiles(rng, 1).iloc[0].to_dict())
    context = TripContext(
        city="Seattle",
        season="fall",
        weather="light_rain",
        ambient_temp_c=11.0,
        humidity=0.77,
        wind_speed_kmh=14.0,
        precipitation_mm=2.3,
        departure_hour=17,
        day_type="weekday",
        trip_purpose="business",
        road_type="arterial",
        traffic_level=0.69,
        expected_congestion=0.71,
        distance_km=22.0,
        elevation_gain_m=90.0,
        elevation_loss_m=75.0,
        passengers=1,
        cargo_kg=10.0,
    )
    vehicle = _vehicle()
    behavior = sample_behavior_state(rng, driver, vehicle, context)
    config = SimulationConfig()
    baseline = compute_baseline_trip(context, vehicle, behavior, config, rng)
    targets = generate_targets(rng, context, driver, vehicle, behavior, baseline, config)
    assert targets["recommended_mode"] in {"ev", "hybrid", "ice"}
    assert targets["estimated_cost"] != baseline["true_energy_cost"]
    assert targets["estimated_time_min"] != baseline["true_duration_min"]
    assert targets["mode_prob_ev"] >= 0.0
    assert targets["mode_prob_hybrid"] >= 0.0
    assert targets["mode_prob_ice"] >= 0.0
    assert abs(targets["mode_prob_ev"] + targets["mode_prob_hybrid"] + targets["mode_prob_ice"] - 1.0) < 1e-6
