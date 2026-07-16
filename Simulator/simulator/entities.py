"""Dataclasses used by the simulator."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Sequence


@dataclass(frozen=True)
class VehicleProfile:
    vehicle_id: str
    make: str
    model: str
    archetype: str
    powertrain_type: str
    body_type: str
    battery_capacity_kwh: float
    usable_battery_kwh: float
    fuel_tank_l: float
    mass_kg: float
    drag_coeff: float
    frontal_area_m2: float
    rolling_resistance_coeff: float
    drivetrain_efficiency: float
    regen_efficiency: float
    hvac_base_kw: float
    city_efficiency_factor: float
    highway_efficiency_factor: float
    nominal_ev_range_km: float
    battery_health: float
    vehicle_health_factor: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class DriverProfile:
    driver_id: str
    aggressiveness: float
    consistency: float
    eco_awareness: float
    range_anxiety: float
    hvac_preference: float
    speeding_tendency: float
    braking_smoothness: float
    charging_discipline: float
    route_familiarity_bias: float
    preferred_trip_purposes: Sequence[str]
    schedule_pressure: float
    traffic_uncertainty: float
    vehicle_health_factor: float
    battery_health: float
    tire_condition: float

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["preferred_trip_purposes"] = list(self.preferred_trip_purposes)
        return payload


@dataclass(frozen=True)
class CityProfile:
    city: str
    elevation_tendency: float
    urban_congestion: float
    highway_congestion: float
    season_temperature_c: dict
    season_humidity: dict
    season_precip_prob: dict
    season_precip_intensity_mm: dict
    season_wind_kmh: dict
    grid_emissions_kg_per_kwh: float
    electricity_price_per_kwh: float
    fuel_price_per_l: float


@dataclass(frozen=True)
class TripPurposeProfile:
    purpose: str
    distance_mean_km: float
    distance_std_km: float
    departure_hour_mean: float
    departure_hour_std: float
    road_mix: dict
    passenger_mean: float
    passenger_std: float
    cargo_mean_kg: float
    cargo_std_kg: float
    urgency_prior: float
    weekday_preference: float
    weekend_preference: float


@dataclass
class TripContext:
    city: str
    season: str
    weather: str
    ambient_temp_c: float
    humidity: float
    wind_speed_kmh: float
    precipitation_mm: float
    departure_hour: int
    day_type: str
    trip_purpose: str
    road_type: str
    traffic_level: float
    expected_congestion: float
    distance_km: float
    elevation_gain_m: float
    elevation_loss_m: float
    passengers: int
    cargo_kg: float


@dataclass
class BehaviorState:
    speed_factor: float
    stop_go_multiplier: float
    hvac_multiplier: float
    regen_multiplier: float
    route_detour_factor: float
    battery_reserve_soc: float
    speed_variability: float
    harsh_braking_probability: float
