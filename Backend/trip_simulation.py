"""Core real-time trip simulation engine.

Manages the server-side trip state, drives the physics tick loop, and
schedules ML / GenAI prediction cycles based on real wall-clock time.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field, asdict
from typing import Any, Callable

from trip_physics import (
    VehicleSpec,
    compute_range_left,
    compute_regen_energy,
    compute_speed_change,
    compute_tick_energy,
    vehicle_spec_from_db,
)


# ---------------------------------------------------------------------------
# Trip state
# ---------------------------------------------------------------------------

@dataclass
class TripState:
    """Full simulation state pushed to the dashboard every tick."""

    elapsed_sim_seconds: float = 0.0
    distance_traveled_km: float = 0.0
    current_speed_kmh: float = 0.0
    current_acceleration_mps2: float = 0.0
    battery_soc_pct: float = 100.0
    fuel_level_pct: float = 100.0
    regen_energy_kwh: float = 0.0
    co2_emitted_kg: float = 0.0
    trip_cost_usd: float = 0.0
    current_mode: str = "ev"
    switch_point_km: float | None = None
    range_left_km: float = 0.0

    # Cumulative energy
    battery_used_kwh: float = 0.0
    fuel_used_l: float = 0.0

    # ML predictions (updated every ML cycle)
    ml_predictions: dict[str, Any] | None = None
    # GenAI recommendation (updated every GenAI cycle)
    genai_recommendation: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for key, val in d.items():
            if isinstance(val, float):
                d[key] = round(val, 4)
        # Explicit synonyms for clarity
        d["cumulative_fuel_used_l"] = d["fuel_used_l"]
        d["cumulative_battery_used_kwh"] = d["battery_used_kwh"]
        return d


# ---------------------------------------------------------------------------
# Event types emitted by the simulation
# ---------------------------------------------------------------------------

@dataclass
class SimEvent:
    """An event emitted by the simulation for the WebSocket to push."""
    event_type: str          # "tick", "ml_update", "genai_update", "regen_event",
                             # "mode_switch", "voice_event", "trip_end"
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Trip Simulation
# ---------------------------------------------------------------------------

# Intervals in WALL-CLOCK seconds (so speeding up simulation scale/car speed does NOT spam API/ML calls)
ML_INTERVAL_WALL_SECONDS = 10.0
GENAI_INTERVAL_WALL_SECONDS = 30.0

# Low-battery threshold for voice warning
LOW_BATTERY_THRESHOLD_PCT = 15.0

# Speed warning thresholds (km/h)
SPEED_WARNING_URBAN_KMH = 80.0
SPEED_WARNING_GENERAL_KMH = 120.0


class TripSimulation:
    """Manages a single live trip simulation session.

    Parameters
    ----------
    trip_config : dict
        The initial trip configuration.
    vehicle_doc : dict
        Full vehicle document from the database.
    ml_predict_fn : callable
        predict_trip_structured(features_dict)
    genai_fn : callable
        run_recommender_agent(...)
    tts_fn : callable or None
        generate_and_play_tts(text)
    """

    def __init__(
        self,
        trip_config: dict[str, Any],
        vehicle_doc: dict[str, Any],
        ml_predict_fn: Callable,
        genai_fn: Callable,
        tts_fn: Callable | None = None,
    ):
        self.trip_input = trip_config.get("trip_input", {})
        self.user_context = trip_config.get("user_context", {})
        self.vehicle_doc = vehicle_doc
        self.vehicle = vehicle_spec_from_db(vehicle_doc)
        self._ml_predict = ml_predict_fn
        self._genai_fn = genai_fn
        self._tts_fn = tts_fn

        self.total_distance_km = float(self.trip_input.get("distance_km", 10.0))
        self.road_type: str = self.trip_input.get("road_type", "urban")
        self.traffic_level: float = float(self.trip_input.get("traffic_level", 0.5))
        self.passengers: int = int(self.trip_input.get("passengers", 1))
        self.cargo_kg: float = float(self.trip_input.get("cargo_kg", 0.0))
        self.ambient_temp_c: float = float(self.trip_input.get("ambient_temp_c", 20.0))
        self.wind_speed_kmh: float = float(self.trip_input.get("wind_speed_kmh", 0.0))

        # State
        self.state = TripState()
        req_mode = str(self.trip_input.get("mode") or self.trip_input.get("current_mode") or "").lower()
        if self.vehicle.powertrain_type == "ev":
            self.state.current_mode = "ev"
        elif self.vehicle.powertrain_type == "ice":
            self.state.current_mode = "ice"
        else:
            if req_mode in ("ev", "hybrid", "ice"):
                self.state.current_mode = req_mode
            else:
                self.state.current_mode = "hybrid"
        self.state.range_left_km = compute_range_left(self.state.battery_soc_pct, self.state.fuel_level_pct, self.vehicle)

        # User controls
        self._current_action: str = "coast"
        self._time_multiplier: int = 1
        self._voice_enabled: bool = True

        # Scheduling trackers in REAL WALL-CLOCK seconds (so speeding up speed/multiplier won't accelerate ML/GenAI calls)
        self._wall_seconds_since_ml: float = ML_INTERVAL_WALL_SECONDS  # trigger immediately on first tick
        self._wall_seconds_since_genai: float = GENAI_INTERVAL_WALL_SECONDS

        # Event flags
        self._low_battery_warned: bool = False
        self._speed_warned: bool = False
        self._finished: bool = False

    def set_action(self, action: str) -> None:
        if action in ("accelerate", "brake", "coast"):
            self._current_action = action

    def set_time_multiplier(self, value: int) -> None:
        self._time_multiplier = max(1, min(100, value))

    def set_voice_enabled(self, enabled: bool) -> None:
        self._voice_enabled = enabled

    def tick(self, wall_dt_seconds: float = 1.0) -> list[SimEvent]:
        """Advance the simulation by wall_dt_seconds.

        time_multiplier only scales the trip's PROGRESS (distance, energy,
        elapsed simulated time) - it never changes how speed responds to
        pedal input. Speed/acceleration are always computed with a fixed
        1-second step, so pedal response and the speedometer behave
        identically to x1 regardless of the selected multiplier.
        """
        if self._finished:
            return []

        events: list[SimEvent] = []

        old_speed = self.state.current_speed_kmh
        old_mode = self.state.current_mode

        # Scales the trip's progress (distance/energy/elapsed time) with the multiplier.
        progress_dt = wall_dt_seconds * self._time_multiplier
        # Fixed regardless of multiplier: keeps pedal response/speedometer identical to x1.
        SPEED_DT = 1.0

        new_speed, accel = compute_speed_change(
            self.state.current_speed_kmh,
            self._current_action,
            self.road_type,
            self.traffic_level,
            SPEED_DT,
        )

        total_regen_kwh = 0.0
        if new_speed < old_speed and self._current_action == "brake":
            total_regen_kwh = compute_regen_energy(
                old_speed, new_speed, self.vehicle,
                self.passengers, self.cargo_kg,
            )
            if self.vehicle.usable_battery_kwh > 0:
                regen_pct = (total_regen_kwh / self.vehicle.usable_battery_kwh) * 100.0
                self.state.battery_soc_pct = min(100.0, self.state.battery_soc_pct + regen_pct)
            self.state.regen_energy_kwh += total_regen_kwh

        self.state.current_speed_kmh = new_speed
        self.state.current_acceleration_mps2 = accel

        avg_speed = (old_speed + new_speed) / 2.0

        energy = compute_tick_energy(
            avg_speed, max(0, accel), self.vehicle,
            old_mode, progress_dt,
            self.passengers, self.cargo_kg,
            self.ambient_temp_c, self.wind_speed_kmh,
        )

        self.state.distance_traveled_km += energy["distance_km"]
        self.state.battery_used_kwh += energy["battery_used_kwh"]
        self.state.fuel_used_l += energy["fuel_used_l"]
        self.state.co2_emitted_kg += energy["co2_kg"]
        self.state.trip_cost_usd += energy["cost_usd"]
        self.state.elapsed_sim_seconds += progress_dt

        if self.vehicle.usable_battery_kwh > 0:
            used_pct = (energy["battery_used_kwh"] / self.vehicle.usable_battery_kwh) * 100.0
            self.state.battery_soc_pct = max(0.0, self.state.battery_soc_pct - used_pct)
        if self.vehicle.fuel_tank_l > 0:
            used_pct = (energy["fuel_used_l"] / self.vehicle.fuel_tank_l) * 100.0
            self.state.fuel_level_pct = max(0.0, self.state.fuel_level_pct - used_pct)

        self.state.range_left_km = compute_range_left(self.state.battery_soc_pct, self.state.fuel_level_pct, self.vehicle)

        if self.state.battery_soc_pct <= 0.0 and self.vehicle.powertrain_type != "ice":
            if self.state.current_mode != "ice" and self.vehicle.fuel_tank_l > 0:
                self.state.current_mode = "ice"

        if self.state.distance_traveled_km >= self.total_distance_km:
            self.state.distance_traveled_km = self.total_distance_km
            end_events = self._end_trip("Trip distance completed.")
            events.extend(end_events)
            return events

        if total_regen_kwh > 0:
            events.append(SimEvent("regen_event", {
                "energy_recovered_kwh": round(total_regen_kwh, 4),
                "total_regen_kwh": round(self.state.regen_energy_kwh, 4),
                "new_soc_pct": round(self.state.battery_soc_pct, 2),
            }))

        # --- ML prediction cycle (every 10 REAL WALL-CLOCK seconds) ---------------
        self._wall_seconds_since_ml += wall_dt_seconds
        if self._wall_seconds_since_ml >= ML_INTERVAL_WALL_SECONDS:
            self._wall_seconds_since_ml = 0.0
            ml_events = self._run_ml_prediction()
            events.extend(ml_events)

        # --- GenAI cycle (every 30 REAL WALL-CLOCK seconds) -----------------------
        self._wall_seconds_since_genai += wall_dt_seconds
        if self._wall_seconds_since_genai >= GENAI_INTERVAL_WALL_SECONDS:
            self._wall_seconds_since_genai = 0.0
            genai_events = self._run_genai_prediction()
            events.extend(genai_events)

        # Event detection
        if self.state.current_mode != old_mode:
            reason = self._mode_switch_reason(old_mode, self.state.current_mode)
            events.append(SimEvent("mode_switch", {
                "from": old_mode,
                "to": self.state.current_mode,
                "reason": reason,
            }))
            if self._voice_enabled:
                voice_text = f"Switching to {self.state.current_mode.upper()} mode. {reason}"
                events.append(SimEvent("voice_event", {
                    "event": "mode_switch",
                    "text": voice_text,
                }))
                self._fire_tts(voice_text)

        if (self.state.battery_soc_pct < LOW_BATTERY_THRESHOLD_PCT
                and not self._low_battery_warned
                and self.vehicle.powertrain_type != "ice"):
            self._low_battery_warned = True
            warn_text = f"Warning: battery level low at {self.state.battery_soc_pct:.0f}%."
            events.append(SimEvent("voice_event", {
                "event": "low_battery",
                "text": warn_text,
            }))
            if self._voice_enabled:
                self._fire_tts(warn_text)

        speed_limit = SPEED_WARNING_URBAN_KMH if self.road_type == "urban" else SPEED_WARNING_GENERAL_KMH
        if self.state.current_speed_kmh > speed_limit and not self._speed_warned:
            self._speed_warned = True
            warn_text = f"Speed warning: {self.state.current_speed_kmh:.0f} km/h exceeds recommended limit for {self.road_type} road."
            events.append(SimEvent("voice_event", {
                "event": "speed_warning",
                "text": warn_text,
            }))
            if self._voice_enabled:
                self._fire_tts(warn_text)
        elif self.state.current_speed_kmh <= speed_limit * 0.9:
            self._speed_warned = False

        events.insert(0, SimEvent("tick", {"state": self.state.to_dict()}))
        return events

    def stop(self) -> list[SimEvent]:
        return self._end_trip("Trip stopped by user.")

    def _end_trip(self, reason: str) -> list[SimEvent]:
        if self._finished:
            return []
        self._finished = True
        events: list[SimEvent] = []

        ml_events = self._run_ml_prediction()
        events.extend(ml_events)

        genai_events = self._run_genai_prediction()
        events.extend(genai_events)

        summary = {
            "reason": reason,
            "final_state": self.state.to_dict(),
            "ml_predictions": self.state.ml_predictions,
            "genai_recommendation": self.state.genai_recommendation,
        }
        events.append(SimEvent("trip_end", summary))

        if self._voice_enabled and self.state.genai_recommendation:
            end_text = self.state.genai_recommendation.get("summary", reason)
            events.append(SimEvent("voice_event", {
                "event": "trip_end",
                "text": end_text,
            }))
            self._fire_tts(end_text)

        return events

    @property
    def is_finished(self) -> bool:
        return self._finished

    def _run_ml_prediction(self) -> list[SimEvent]:
        events: list[SimEvent] = []
        try:
            features = self._build_ml_features()
            result = self._ml_predict(features)
            self.state.ml_predictions = result

            raw = result.get("raw", {})
            new_mode = str(raw.get("recommended_mode", self.state.current_mode)).lower()

            if self.vehicle.powertrain_type == "ev" and new_mode == "ice":
                new_mode = "ev"
            elif self.vehicle.powertrain_type == "ice" and new_mode == "ev":
                new_mode = "ice"
            if self.state.battery_soc_pct <= 0 and new_mode == "ev":
                new_mode = "ice" if self.vehicle.fuel_tank_l > 0 else new_mode

            self.state.current_mode = new_mode
            self.state.switch_point_km = raw.get("switch_point_km")

            events.append(SimEvent("ml_update", {
                "predictions": result,
                "current_mode": new_mode,
            }))
        except Exception as exc:
            events.append(SimEvent("ml_update", {
                "error": str(exc),
            }))
        return events

    def _build_ml_features(self) -> dict[str, Any]:
        specs = self.vehicle_doc.get("specifications", {})
        return {
            "make": self.trip_input.get("make", ""),
            "model": self.trip_input.get("model", ""),
            "powertrain_type": self.vehicle.powertrain_type,
            "body_type": specs.get("bodyType", self.trip_input.get("body_type", "sedan")),
            "battery_capacity_kwh": float(specs.get("batteryCapacityKwh", 0.0)),
            "usable_battery_kwh": self.vehicle.usable_battery_kwh,
            "fuel_tank_l": self.vehicle.fuel_tank_l,
            "mass_kg": self.vehicle.mass_kg,
            "drag_coeff": self.vehicle.drag_coeff,
            "frontal_area_m2": self.vehicle.frontal_area_m2,
            "city": self.trip_input.get("city", "Chicago"),
            "season": self.trip_input.get("season", "fall"),
            "weather": self.trip_input.get("weather", "clear"),
            "ambient_temp_c": self.ambient_temp_c,
            "humidity": float(self.trip_input.get("humidity", 0.5)),
            "wind_speed_kmh": self.wind_speed_kmh,
            "precipitation_mm": float(self.trip_input.get("precipitation_mm", 0.0)),
            "departure_hour": int(self.trip_input.get("departure_hour", 12)),
            "day_type": self.trip_input.get("day_type", "weekday"),
            "trip_purpose": self.trip_input.get("trip_purpose", "commute"),
            "road_type": self.road_type,
            "traffic_level": self.traffic_level,
            "distance_km": max(0.1, self.state.distance_traveled_km),
            "passengers": self.passengers,
            "cargo_kg": self.cargo_kg,
        }

    def _run_genai_prediction(self) -> list[SimEvent]:
        events: list[SimEvent] = []
        try:
            enriched_input = dict(self.trip_input)
            enriched_input["current_speed_kmh"] = self.state.current_speed_kmh
            enriched_input["distance_traveled_km"] = self.state.distance_traveled_km
            enriched_input["battery_soc_pct"] = self.state.battery_soc_pct
            enriched_input["fuel_level_pct"] = self.state.fuel_level_pct
            enriched_input["regen_energy_kwh"] = self.state.regen_energy_kwh
            enriched_input["current_mode"] = self.state.current_mode
            enriched_input["elapsed_minutes"] = self.state.elapsed_sim_seconds / 60.0

            ml_metrics = self.state.ml_predictions or {}
            result = self._genai_fn(
                user_input=enriched_input,
                vehicle_data=self.vehicle_doc,
                ml_metrics=ml_metrics,
                user_context=self.user_context,
            )
            self.state.genai_recommendation = result
            events.append(SimEvent("genai_update", {
                "recommendation": result,
            }))
        except Exception as exc:
            events.append(SimEvent("genai_update", {
                "error": str(exc),
            }))
        return events

    def _fire_tts(self, text: str) -> None:
        if self._tts_fn and self._voice_enabled:
            threading.Thread(
                target=self._tts_fn,
                args=(text,),
                daemon=True,
            ).start()

    @staticmethod
    def _mode_switch_reason(old_mode: str, new_mode: str) -> str:
        if old_mode == "ev" and new_mode in ("ice", "hybrid"):
            return "Battery depleted or high-speed driving detected."
        if old_mode == "ice" and new_mode in ("ev", "hybrid"):
            return "Lower speed or favorable conditions for electric driving."
        if old_mode == "hybrid" and new_mode == "ev":
            return "Conditions favor pure electric mode."
        if old_mode == "hybrid" and new_mode == "ice":
            return "High power demand requires combustion engine."
        return "Driving conditions changed."


def build_trip_start_announcement(
    vehicle_doc: dict[str, Any],
    trip_input: dict[str, Any],
) -> str:
    name = vehicle_doc.get("vehicle_name", "your vehicle")
    dist = trip_input.get("distance_km", "?")
    road = trip_input.get("road_type", "road")
    weather = trip_input.get("weather", "clear")
    return (
        f"Starting trip with {name}. "
        f"{dist} kilometers on {road} road, {weather} weather. "
        f"Drive safely."
    )
