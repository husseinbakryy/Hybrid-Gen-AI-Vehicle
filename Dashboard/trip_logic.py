"""
Trip planning logic - the "brain" of the app.

Deliberately has ZERO PyQt imports. Everything here is plain Python: numbers
in, numbers/text out. This is where the real trained ML model and the GenAI
recommendation call will eventually replace the placeholder logic below -
whoever works on that doesn't need to touch any UI code, and whoever works
on the UI doesn't need to understand the model to call these functions.

Current state: rule-based placeholders (see NOTE comments). Not the real model.
"""

import json
from datetime import datetime

GAS_RANGE_ASSUMED = 480      # miles - placeholder assumption, not from real data
CHARGE_STOP_MINUTES = 15     # placeholder assumption for a charging stop's duration
EV_COST_PER_MILE = 0.073     # NOTE: placeholder flat rate, not the trained model
GAS_COST_PER_MILE = 0.103    # NOTE: placeholder flat rate, not the trained model
CO2_PER_GAS_MILE = 0.04      # NOTE: placeholder, not sourced from real emissions data

# These are confirmed fixed values for the current prototype.
CITY = "Chicago"
SEASON = "fall"

# PLACEHOLDER - replace with teammate's real vehicle list.
VEHICLE_CATALOG = {
    "Nexa VoltMini": {"make": "Nexa", "model": "VoltMini"},
    "Aster Luma 5": {"make": "Aster", "model": "Luma 5"},
    "Orion Pulse H": {"make": "Orion", "model": "Pulse H"},
    "Terra Trail H": {"make": "Terra", "model": "Trail H"},
    "Helio Cruze L": {"make": "Helio", "model": "Cruze L"},
    "Helio Rover X": {"make": "Helio", "model": "Rover X"},
}


def _placeholder_efficiency_modifier(temperature: int | None, traffic: str | None,
                                      style: str | None) -> float:
    """NOTE: placeholder rule-based efficiency modifier, not from real model."""
    modifier = 1.0
    if temperature is not None:
        if temperature < 0:
            modifier *= 0.94
        elif temperature > 30:
            modifier *= 0.97

    if traffic is not None:
        traffic_value = traffic.lower()
        if traffic_value == "high":
            modifier *= 0.93
        elif traffic_value == "medium":
            modifier *= 0.97

    if style is not None:
        style_value = style.lower()
        if style_value == "aggressive":
            modifier *= 0.95
        elif style_value == "eco":
            modifier *= 1.04

    return max(modifier, 0.1)


def compute_mode_segments(distance: float, ev_range: float, stops: list[int],
                           temperature: int | None = None, traffic: str | None = None,
                           style: str | None = None) -> list[list]:
    """Split a trip into alternating Electric/Gas segments given an EV range
    per full charge and a list of mile-marks where the battery is recharged
    to full (manual charging stops). Returns [[start_mi, end_mi, mode], ...].

    NOTE: this is the rule-based placeholder ("EV until battery empty, then
    gas, recharge at each stop"). Once the trained model is ready, this is
    likely what gets replaced or augmented with a real prediction.
    """
    efficiency = _placeholder_efficiency_modifier(temperature, traffic, style)
    effective_ev_range = ev_range * efficiency

    stops = sorted(s for s in stops if 0 < s < distance)
    boundaries = stops + [distance]

    segments = []
    pos = 0.0
    battery_range = effective_ev_range
    for boundary in boundaries:
        span = boundary - pos
        if battery_range >= span:
            segments.append([pos, boundary, "Electric"])
            battery_range -= span
        else:
            ev_end = pos + max(0.0, battery_range)
            if ev_end > pos:
                segments.append([pos, ev_end, "Electric"])
            segments.append([ev_end, boundary, "Gas"])
            battery_range = 0.0
        if boundary != distance:
            battery_range = effective_ev_range  # recharge to full at this stop
        pos = boundary

    merged = [segments[0]]
    for seg in segments[1:]:
        if merged[-1][2] == seg[2] and merged[-1][1] == seg[0]:
            merged[-1][1] = seg[1]
        else:
            merged.append(seg)
    return merged


def compute_trip_stats(segments: list[list], stops: list[int], distance: float,
                        speed: float, temperature: int | None = None,
                        traffic: str | None = None, style: str | None = None) -> dict:
    """Cost, time, CO2, and range-left for a finished trip plan.

    NOTE: cost/CO2 use flat placeholder rates (EV_COST_PER_MILE,
    GAS_COST_PER_MILE, CO2_PER_GAS_MILE), not your team's real trained model
    or dataset-derived figures. Swap the guts of this function once that's
    ready - the return shape (a dict with these exact keys) is what the UI
    expects, so keep that the same if you want main_window.py to keep working
    unmodified.
    """
    efficiency = _placeholder_efficiency_modifier(temperature, traffic, style)
    ev_miles = sum(e - s for s, e, m in segments if m == "Electric")
    gas_miles = sum(e - s for s, e, m in segments if m == "Gas")

    cost = (ev_miles * EV_COST_PER_MILE + gas_miles * GAS_COST_PER_MILE) * efficiency
    drive_hrs = distance / speed
    charge_hrs = len(stops) * CHARGE_STOP_MINUTES / 60
    total_hrs = (drive_hrs + charge_hrs) / efficiency
    hh, mm = int(total_hrs), round((total_hrs - int(total_hrs)) * 60)
    co2 = gas_miles * CO2_PER_GAS_MILE
    range_left = max(0, GAS_RANGE_ASSUMED - gas_miles)

    return {
        "ev_miles": ev_miles,
        "gas_miles": gas_miles,
        "cost": cost,
        "hours": total_hrs,
        "hh": hh,
        "mm": mm,
        "co2": co2,
        "range_left": range_left,
    }


def describe_segments(segments: list[list], stops: list[int], cost: float,
                       hh: int, mm: int) -> str:
    """Plain-English trip summary.

    NOTE: this is a hand-written f-string, not a real GenAI call. Once the
    GenAI integration is ready, this function's job is to build the PROMPT
    (trip segments, stops, cost, time) and return the model's generated text
    instead of formatting it directly - same return type (a string), so the
    UI layer (RecommendationPanel.set_text) doesn't need to change.
    """
    parts = [f"{mode} {round(start)}-{round(end)} km" for start, end, mode in segments]
    plan = ", then ".join(parts)
    stop_note = (
        f" Recharge at {', '.join(str(round(s)) + ' km' for s in stops)}."
        if stops else ""
    )
    return f"{plan}.{stop_note} Estimated cost ${cost:.2f}, arriving in {hh}h {mm}m."


def precipitation_from_weather(weather: str) -> float:
    """Derive precipitation (mm) from a selected weather label."""
    mapping = {
        "clear": 0.06,
        "cloudy": 0.07,
        "foggy": 0.09,
        "light_rain": 2.26,
        "heavy_rain": 8.64,
        "snow": 6.08,
        "windy": 0.05,
    }
    return mapping.get(weather, 0.06)


def traffic_level_to_float(selection: str) -> float:
    mapping = {
        "Low": 0.35,
        "Medium": 0.65,
        "High": 0.95,
    }
    return mapping.get(selection, 0.65)


def style_to_preferred_mode(style: str) -> str:
    return style.lower()


def build_trip_payload(
    vehicle: str = "Nexa VoltMini",
    weather: str = "clear",
    temp: float = 20.0,
    humidity: float = 0.5,
    wind: float = 0.0,
    trip_purpose: str = "commute",
    road_type: str = "urban",
    traffic: str = "Medium",
    distance: float = 10.0,
    passengers: int = 1,
    cargo: float = 0.0,
    style: str = "Normal",
) -> dict:
    if vehicle not in VEHICLE_CATALOG:
        raise ValueError(f"Unknown vehicle: {vehicle}")

    vehicle_data = VEHICLE_CATALOG[vehicle]
    departure_hour = datetime.now().hour
    day_type = "weekend" if datetime.now().weekday() >= 5 else "weekday"

    return {
        "trip_input": {
            "make": vehicle_data["make"],
            "model": vehicle_data["model"],
            "city": CITY,
            "season": SEASON,
            "weather": weather,
            "ambient_temp_c": temp,
            "humidity": humidity,
            "wind_speed_kmh": wind,
            "precipitation_mm": precipitation_from_weather(weather),
            "departure_hour": departure_hour,
            "day_type": day_type,
            "trip_purpose": trip_purpose,
            "road_type": road_type,
            "traffic_level": traffic_level_to_float(traffic),
            "distance_km": distance,
            "passengers": passengers,
            "cargo_kg": cargo,
        },
        "user_context": {
            "preferred_mode": style_to_preferred_mode(style),
            # NOTE: hardcoded for this dashboard version; may become dynamic later.
            "notes": "Generated by Hybrid Drive Assist dashboard",
        },
    }


def build_trip_payload_json(**kwargs) -> str:
    return json.dumps(build_trip_payload(**kwargs), indent=2)
