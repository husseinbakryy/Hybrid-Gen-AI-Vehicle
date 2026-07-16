"""Public API for the procedural stochastic trip simulator."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from .behavior import sample_behavior_state
from .config import SimulationConfig
from .drivers import generate_driver_profiles
from .entities import DriverProfile, TripContext, VehicleProfile
from .environment import CITY_PROFILES, SEASONS, sample_environment
from .labels import generate_targets
from .noise import apply_measurement_noise
from .physics import compute_baseline_trip
from .trip_purposes import choose_trip_purpose, sample_trip_purpose_context
from .vehicles import generate_vehicle_fleet


class TripSimulator:
    """Generate synthetic trips with latent state, physics, behavior, and noisy observations."""

    def __init__(self, seed: int = 42, config: Optional[dict] = None):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.config = SimulationConfig(**config) if config else SimulationConfig()
        self._drivers: pd.DataFrame | None = None
        self._vehicles: pd.DataFrame | None = None
        self._driver_vehicle_map: dict[str, str] = {}
        self._vehicle_soc_state: dict[str, float] = {}

    def generate_drivers(self, n_drivers: int) -> pd.DataFrame:
        self._drivers = generate_driver_profiles(self.rng, n_drivers)
        return self._drivers.copy()

    def generate_vehicles(self) -> pd.DataFrame:
        self._vehicles = generate_vehicle_fleet(self.rng, self.config.default_n_vehicles)
        self._vehicle_soc_state = {row["vehicle_id"]: self._initial_vehicle_soc(row) for row in self._vehicles.to_dict(orient="records")}
        return self._vehicles.copy()

    def _ensure_entities(self, n_drivers: int) -> tuple[pd.DataFrame, pd.DataFrame]:
        drivers = self._drivers if self._drivers is not None and len(self._drivers) == n_drivers else self.generate_drivers(n_drivers)
        vehicles = self._vehicles if self._vehicles is not None else self.generate_vehicles()
        if not self._driver_vehicle_map or len(self._driver_vehicle_map) != len(drivers):
            vehicle_ids = list(vehicles["vehicle_id"].tolist())
            self._driver_vehicle_map = {
                driver_id: vehicle_ids[index % len(vehicle_ids)]
                for index, driver_id in enumerate(drivers["driver_id"].tolist())
            }
        return drivers, vehicles

    def _initial_vehicle_soc(self, vehicle_row: dict) -> float:
        if vehicle_row["powertrain_type"] == "ev":
            return float(np.clip(78.0 + self.rng.normal(0, 6.0), 40.0, 98.0))
        if vehicle_row["powertrain_type"] == "hybrid":
            return float(np.clip(56.0 + self.rng.normal(0, 7.0), 20.0, 90.0))
        return float(np.clip(92.0 + self.rng.normal(0, 1.5), 85.0, 99.0))

    def _update_vehicle_soc(self, vehicle_id: str, vehicle_row: dict, driver_row: dict, behavior, baseline: dict) -> tuple[float, float]:
        start_pct = self._vehicle_soc_state.get(vehicle_id, self._initial_vehicle_soc(vehicle_row))
        if vehicle_row["powertrain_type"] == "ice":
            end_pct = max(0.0, start_pct - 0.03 * (1.0 + behavior.speed_variability))
        else:
            usable = max(vehicle_row["usable_battery_kwh"], 1e-6)
            used_pct = 100.0 * baseline["true_battery_used_kwh"] / usable
            reserve_floor = 100.0 * (0.10 + 0.30 * driver_row["range_anxiety"] + 0.10 * (1.0 - driver_row["charging_discipline"]))
            end_pct = max(reserve_floor, start_pct - used_pct)
        end_pct = min(start_pct, end_pct)
        self._vehicle_soc_state[vehicle_id] = end_pct
        return float(start_pct), float(end_pct)

    def generate_trips(self, n_trips: int, n_drivers: int = 300) -> pd.DataFrame:
        drivers, vehicles = self._ensure_entities(n_drivers)
        driver_records = drivers.to_dict(orient="records")
        vehicle_records = vehicles.to_dict(orient="records")

        activity = self.rng.lognormal(mean=np.log(self.config.driver_activity_mean), sigma=self.config.driver_activity_sigma, size=n_drivers)
        activity = activity / activity.sum()
        driver_trip_counts = self.rng.multinomial(n_trips, activity)

        city_names = list(CITY_PROFILES.keys())
        city_probs = np.array([0.18, 0.22, 0.20, 0.15, 0.25], dtype=float)
        rows: list[dict] = []
        trip_id = 0
        for driver_index, trip_count in enumerate(driver_trip_counts):
            driver = driver_records[driver_index]
            vehicle_id = self._driver_vehicle_map[driver["driver_id"]]
            assigned_vehicle = next(vehicle for vehicle in vehicle_records if vehicle["vehicle_id"] == vehicle_id)
            for driver_trip_index in range(int(trip_count)):
                day_type = self._sample_day_type(driver)
                purpose = choose_trip_purpose(self.rng, driver["preferred_trip_purposes"], day_type)
                purpose_context = sample_trip_purpose_context(self.rng, purpose, day_type)
                city = str(self.rng.choice(city_names, p=city_probs))
                season = str(self.rng.choice(list(SEASONS)))
                env = sample_environment(
                    self.rng,
                    city=city,
                    season=season,
                    departure_hour=purpose_context["departure_hour"],
                    day_type=day_type,
                    road_type=purpose_context["road_type"],
                    trip_purpose=purpose,
                    distance_km=purpose_context["distance_km"],
                )

                context = TripContext(
                    city=city,
                    season=season,
                    weather=env["weather"],
                    ambient_temp_c=env["ambient_temp_c"],
                    humidity=env["humidity"],
                    wind_speed_kmh=env["wind_speed_kmh"],
                    precipitation_mm=env["precipitation_mm"],
                    departure_hour=purpose_context["departure_hour"],
                    day_type=day_type,
                    trip_purpose=purpose,
                    road_type=purpose_context["road_type"],
                    traffic_level=env["traffic_level"],
                    expected_congestion=env["expected_congestion"],
                    distance_km=purpose_context["distance_km"],
                    elevation_gain_m=env["elevation_gain_m"],
                    elevation_loss_m=env["elevation_loss_m"],
                    passengers=purpose_context["passengers"],
                    cargo_kg=purpose_context["cargo_kg"],
                )

                driver_profile = DriverProfile(**driver)
                vehicle_profile = VehicleProfile(**assigned_vehicle)
                behavior = sample_behavior_state(self.rng, driver_profile, vehicle_profile, context)
                adjusted_context = TripContext(
                    **{**context.__dict__, "distance_km": context.distance_km * behavior.route_detour_factor}
                )
                baseline = compute_baseline_trip(adjusted_context, vehicle_profile, behavior, self.config, self.rng)
                soc_start_pct, soc_end_pct = self._update_vehicle_soc(vehicle_id, assigned_vehicle, driver, behavior, baseline)
                baseline.update(
                    {
                        "trip_id": f"trip_{trip_id:07d}",
                        "driver_trip_index": int(driver_trip_index),
                        "driver_id": driver["driver_id"],
                        "vehicle_id": vehicle_id,
                        "driver_vehicle_pair_id": f'{driver["driver_id"]}|{vehicle_id}',
                        "city": city,
                        "season": season,
                        "weather": env["weather"],
                        "ambient_temp_c": env["ambient_temp_c"],
                        "humidity": env["humidity"],
                        "wind_speed_kmh": env["wind_speed_kmh"],
                        "precipitation_mm": env["precipitation_mm"],
                        "departure_hour": purpose_context["departure_hour"],
                        "day_type": day_type,
                        "trip_purpose": purpose,
                        "road_type": purpose_context["road_type"],
                        "traffic_level": env["traffic_level"],
                        "expected_congestion": env["expected_congestion"],
                        "distance_km": adjusted_context.distance_km,
                        "base_distance_km": context.distance_km,
                        "elevation_gain_m": env["elevation_gain_m"],
                        "elevation_loss_m": env["elevation_loss_m"],
                        "passengers": purpose_context["passengers"],
                        "cargo_kg": purpose_context["cargo_kg"],
                        "behavior_speed_factor": behavior.speed_factor,
                        "behavior_stop_go_multiplier": behavior.stop_go_multiplier,
                        "behavior_hvac_multiplier": behavior.hvac_multiplier,
                        "behavior_regen_multiplier": behavior.regen_multiplier,
                        "behavior_route_detour_factor": behavior.route_detour_factor,
                        "behavior_battery_reserve_soc": behavior.battery_reserve_soc,
                        "behavior_speed_variability": behavior.speed_variability,
                        "behavior_harsh_braking_probability": behavior.harsh_braking_probability,
                        "true_battery_soc_start_pct": soc_start_pct,
                        "true_battery_soc_end_pct": soc_end_pct,
                        "battery_soc_start": soc_start_pct / 100.0,
                        "battery_soc_end": soc_end_pct / 100.0,
                        "soc_pct": soc_start_pct,
                    }
                )
                targets = generate_targets(self.rng, adjusted_context, driver_profile, vehicle_profile, behavior, baseline, self.config)
                record = {**driver, **assigned_vehicle, **baseline, **targets}
                record.update(apply_measurement_noise(self.rng, record, self.config))
                rows.append(record)
                trip_id += 1

        df = pd.DataFrame(rows)
        return df.sort_values(["driver_id", "trip_id"]).reset_index(drop=True)

    def _sample_day_type(self, driver: dict) -> str:
        weekday_bias = self.config.workday_trip_share + 0.10 * driver["schedule_pressure"] + 0.08 * driver["route_familiarity_bias"]
        weekday_bias = float(np.clip(weekday_bias, 0.15, 0.95))
        return "weekday" if self.rng.random() < weekday_bias else "weekend"

