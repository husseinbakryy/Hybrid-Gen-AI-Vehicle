"""
Trip planning logic - the "brain" of the app.

Deliberately has ZERO PyQt imports. Everything here is plain Python: numbers
in, numbers/text out. This is where the real trained ML model and the GenAI
recommendation call will eventually replace the placeholder logic below -
whoever works on that doesn't need to touch any UI code, and whoever works
on the UI doesn't need to understand the model to call these functions.

Current state: rule-based placeholders (see NOTE comments). Not the real model.
"""

GAS_RANGE_ASSUMED = 480
CHARGE_STOP_MINUTES = 15
EV_COST_PER_MILE = 0.073
GAS_COST_PER_MILE = 0.103
CO2_PER_GAS_MILE = 0.04


def _placeholder_efficiency_modifier(temperature: int | None, traffic: str | None,
                                      style: str | None) -> float:
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
            battery_range = effective_ev_range
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
    ev_miles = sum(e - s for s, e, m in segments if m == "Electric")
    gas_miles = sum(e - s for s, e, m in segments if m == "Gas")

    cost = ev_miles * EV_COST_PER_MILE + gas_miles * GAS_COST_PER_MILE

    traffic_delay = {"high": 1.18, "medium": 1.07}.get((traffic or "").lower(), 1.0)
    drive_hrs = (distance / speed) * traffic_delay
    charge_hrs = len(stops) * CHARGE_STOP_MINUTES / 60
    total_hrs = drive_hrs + charge_hrs
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
    parts = [f"{mode} {round(start)}-{round(end)}mi" for start, end, mode in segments]
    plan = ", then ".join(parts)
    stop_note = (
        f" Recharge at {', '.join(str(round(s)) + 'mi' for s in stops)}."
        if stops else ""
    )
    return f"{plan}.{stop_note} Estimated cost ${cost:.2f}, arriving in {hh}h {mm}m."
