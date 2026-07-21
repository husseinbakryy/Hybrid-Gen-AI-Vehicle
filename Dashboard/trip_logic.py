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

# requests is used to fetch the live vehicle catalog from the teammate backend.
# Keep this dependency minimal (requests) so the rest of the file remains
# plain Python. On failure, the code falls back to the bundled VEHICLE_CATALOG.
try:
    import requests
except Exception:  # pragma: no cover - environment may not have requests installed
    requests = None

GAS_RANGE_ASSUMED = 480      # miles - placeholder assumption, not from real data
CHARGE_STOP_MINUTES = 15     # placeholder assumption for a charging stop's duration
EV_COST_PER_MILE = 0.073     # NOTE: placeholder flat rate, not the trained model
GAS_COST_PER_MILE = 0.103    # NOTE: placeholder flat rate, not the trained model
CO2_PER_GAS_MILE = 0.04      # NOTE: placeholder, not sourced from real emissions data

# These are confirmed fixed values for the current prototype.
CITY = "Chicago"
SEASON = "fall"

# At startup this is intentionally empty; the app fetches the live
# vehicle catalog from the backend. If the backend is unavailable at
# startup the catalog will remain empty and the UI will show a clear
# inline message. Do NOT hardcode a fallback list here.
VEHICLE_CATALOG: dict = {}

# Nominal per-vehicle EV ranges (km) derived from Data/synthetic_trips.csv.
# Kept local so the UI's placeholder time/range math has consistent inputs
# even when the backend's catalog doesn't include an ev_range field.
# Values (do not change without re-running aggregation on the dataset):
NOMINAL_EV_RANGE_KM = {
    "Aster Luma 5": 441,
    "Nexa VoltMini": 331,
    "Orion Pulse H": 63,
    "Terra Trail H": 61,
    "Helio Rover X": 13,
    "Helio Cruze L": 4,
}


def fetch_vehicle_catalog(base_url: str = "http://localhost:8000", timeout: float = 2.0) -> dict:
    """Fetch vehicle catalog from teammate backend and normalize to the
    local VEHICLE_CATALOG shape: display_name -> {make, model, body_type,
    powertrain_type_display}.

    On any failure (requests not installed, connection error, timeout, bad
    JSON, non-200 status), print a one-line warning and return the bundled
    VEHICLE_CATALOG as a graceful fallback.
    """
    # If requests is unavailable for any reason, fall back immediately.
    if requests is None:
        print(f"[trip_logic] requests library not available, vehicle catalog unavailable")
        return {}

    url = f"{base_url.rstrip('/')}/api/vehicles?unique=true"
    try:
        resp = requests.get(url, timeout=timeout)
        if resp.status_code != 200:
            print(f"[trip_logic] Could not reach backend at {base_url}, vehicle catalog unavailable")
            return {}

        data = resp.json()
        vehicles = data.get("vehicles")
        if not isinstance(vehicles, list):
            print(f"[trip_logic] Unexpected vehicle response shape, vehicle catalog unavailable")
            return {}

        out = {}
        for v in vehicles:
            vehicle_name = v.get("vehicle_name")
            name = v.get("name")
            body_type = v.get("body_type")
            power_train_type = v.get("power_train_type")

            if not vehicle_name or not name:
                # Skip malformed entries but continue processing others
                continue

            make = name
            model = vehicle_name
            prefix = f"{name} "
            if vehicle_name.startswith(prefix):
                model = vehicle_name[len(prefix):]
            else:
                # Degrade gracefully if naming doesn't match - log a warning.
                print(f"[trip_logic] Warning: vehicle_name '{vehicle_name}' does not start with name '{name}', using full vehicle_name as model")

            display = vehicle_name
            out[display] = {
                "make": make,
                "model": model,
                "body_type": body_type,
                "powertrain_type_display": power_train_type,
            }

        if not out:
            # Nothing parsed - return empty
            print(f"[trip_logic] No valid vehicles in backend response, vehicle catalog unavailable")
            return {}

        return out

    except Exception:
        print(f"[trip_logic] Could not reach backend at {base_url}, vehicle catalog unavailable")
        return {}


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


def minutes_to_hh_mm(total_minutes: float) -> tuple[int, int]:
    """Convert a total-minutes float (e.g. trip_time_min from the backend)
    into (hours, minutes), same rounding approach as compute_trip_stats'
    hh/mm derivation from total_hrs."""
    total_hrs = total_minutes / 60
    hh = int(total_hrs)
    mm = round((total_hrs - hh) * 60)
    return hh, mm


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
