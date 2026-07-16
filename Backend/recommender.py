from typing import Any



def _build_recommendation_text(trip_input: dict[str, Any], ml_output: dict[str, Any], user_context: dict[str, Any]) -> str:
    mode = ml_output["recommended_mode"]
    cost = ml_output["trip_cost_usd"]
    co2 = ml_output["co2_emissions_kg"]
    distance = float(trip_input.get("distance_km", 0.0))
    passengers = int(trip_input.get("passengers", 1))

    if mode == "ev":
        primary_tip = "Prefer EV mode for this trip to minimize cost and emissions."
    elif mode == "hybrid":
        primary_tip = "Use hybrid mode and keep steady speeds in traffic-heavy segments."
    else:
        primary_tip = "Use efficient ICE driving style with smoother acceleration and reduced idling."

    comfort_pref = user_context.get("comfort_priority")
    if comfort_pref:
        comfort_line = f"Comfort priority is set to '{comfort_pref}', so keep HVAC and acceleration settings balanced."
    else:
        comfort_line = "If comfort is important, gradually adjust HVAC instead of max bursts to control energy use."

    return (
        f"Trip distance is {distance:.1f} km with {passengers} passenger(s). "
        f"Predicted cost is ${cost:.2f} and CO2 is {co2:.2f} kg. "
        f"{primary_tip} {comfort_line}"
    )



def generate_recommendation(
    trip_input: dict[str, Any],
    ml_output: dict[str, Any],
    user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_context = user_context or {}

    recommendation_text = _build_recommendation_text(trip_input, ml_output, user_context)

    return {
        "summary": recommendation_text,
        "suggested_mode": ml_output["recommended_mode"],
        "actions": [
            "Avoid rapid acceleration in dense traffic.",
            "Plan route to reduce stop-and-go segments where possible.",
            "Monitor HVAC usage when ambient conditions are mild.",
        ],
        "confidence": "medium",
        "source": "genai-recommender-v1",
    }
