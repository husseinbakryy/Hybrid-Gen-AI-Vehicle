from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from dotenv import load_dotenv

load_dotenv(override=True)

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")

def build_agent_prompt(
    user_input: dict[str, Any],
    vehicle_data: dict[str, Any],
    ml_metrics: dict[str, Any],
    user_context: dict[str, Any] | None = None,
) -> str:
    user_ctx_str = json.dumps(user_context or {}, default=str)
    return (
        "You are an expert Intelligent Vehicle Recommender & Trip Planning Agent.\n"
        "Your task is to analyze the user's trip conditions, vehicle specifications, user preferences, "
        "and the 7 machine learning pipeline predictive outputs to synthesize a dynamic, tailored trip plan.\n\n"
        f"1. User Trip Input: {json.dumps(user_input, default=str)}\n"
        f"2. User Preferences & Context: {user_ctx_str}\n"
        f"3. Vehicle Database Specifications: {json.dumps(vehicle_data, default=str)}\n"
        f"4. ML Pipeline 7-Target Predictions: {json.dumps(ml_metrics, default=str)}\n\n"
        "CRITICAL INSTRUCTIONS:\n"
        "- Do NOT return generic, constant, or hardcoded boilerplate summaries.\n"
        "- Synthesize the specific numbers provided above: trip distance, weather, road type, vehicle mass, battery capacity, "
        "and all 7 ML pipeline predictions (Recommended Mode, Fuel Used, Battery Used, CO2 Emissions, Financial Cost, Remaining Range, Trip Duration).\n"
        "- Formulate actionable recommendations specific to the current route, weather, and driving mode.\n\n"
        "Return a strict JSON object with these exact keys:\n"
        "{\n"
        '  "summary": "<Dynamic narrative referencing vehicle name, city/route, predicted trip duration, cost, fuel/battery consumption, and mode>",\n'
        '  "suggested_mode": "<Recommended driving mode>",\n'
        '  "actions": ["<Action 1>", "<Action 2>", "<Action 3>"],\n'
        '  "confidence": "high" | "medium" | "low",\n'
        '  "rationale": "<Technical rationale tying ML predictions to route conditions and vehicle specs>",\n'
        '  "key_factors": ["<Factor 1>", "<Factor 2>", "<Factor 3>"]\n'
        "}"
    )

def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("GenAI response was not a JSON object.")

    return parsed

def run_recommender_agent(
    user_input: dict[str, Any],
    vehicle_data: dict[str, Any],
    ml_metrics: dict[str, Any],
    user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")

    raw_metrics = ml_metrics.get("raw", ml_metrics)

    rec_mode = str(raw_metrics.get("recommended_mode", "hybrid")).upper()
    cost = float(raw_metrics.get("trip_cost_usd", 0.0))
    fuel = float(raw_metrics.get("fuel_used_l", 0.0))
    battery = float(raw_metrics.get("battery_used_kwh", 0.0))
    co2 = float(raw_metrics.get("co2_emissions_kg", 0.0))
    range_left = float(raw_metrics.get("range_left_km", 0.0))
    trip_time = float(raw_metrics.get("trip_time_min", 0.0))

    make = user_input.get("make") or vehicle_data.get("make", "")
    model = user_input.get("model") or vehicle_data.get("model", "")
    veh_name = vehicle_data.get("vehicle_name") or f"{make} {model}".strip() or "Vehicle"
    dist = user_input.get("distance_km", "N/A")
    weather = user_input.get("weather", "normal weather")
    city = user_input.get("city", "the destination")
    road_type = user_input.get("road_type", "road")

    fallback_response = {
        "summary": (
            f"Trip analysis for {veh_name} to {city} ({dist} km, {weather}): "
            f"The ML pipeline recommends {rec_mode} mode, estimating a trip duration of {trip_time:.1f} mins "
            f"and total cost of ${cost:.2f}. Expected energy usage is {fuel:.2f}L fuel and {battery:.2f} kWh battery, "
            f"generating {co2:.2f} kg CO2 with {range_left:.1f} km range remaining."
        ),
        "suggested_mode": rec_mode.lower(),
        "actions": [
            f"Drive efficiently on {road_type} routes to optimize {rec_mode} mode power distribution.",
            f"Monitor battery SoC and remaining range ({range_left:.1f} km) under current ambient conditions ({user_input.get('ambient_temp_c', 20)}°C).",
            f"Account for traffic congestion (level {user_input.get('traffic_level', 0.5)}) and {weather} when planning braking.",
        ],
        "confidence": "high",
        "rationale": (
            f"Evaluated vehicle specifications and route features ({dist} km, traffic {user_input.get('traffic_level')}, {weather}). "
            f"{rec_mode} mode balances trip cost (${cost:.2f}), carbon footprint ({co2:.2f} kg), and battery/fuel consumption."
        ),
        "key_factors": [
            f"distance_km ({dist})",
            f"road_type ({road_type})",
            f"weather ({weather})",
            f"traffic_level ({user_input.get('traffic_level')})",
        ],
    }

    if not api_key:
        return fallback_response

    prompt = build_agent_prompt(user_input, vehicle_data, ml_metrics, user_context=user_context)
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    req = request.Request(
        OPENROUTER_CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Hybrid-Vehicle-Agent"),
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
        choices = response_payload.get("choices") or []
        if not choices:
            return fallback_response
        content = choices[0].get("message", {}).get("content", "")
        parsed = _extract_json(content)
        parsed.setdefault("suggested_mode", rec_mode.lower())
        parsed.setdefault("summary", fallback_response["summary"])
        parsed.setdefault("actions", fallback_response["actions"])
        parsed.setdefault("confidence", "high")
        parsed.setdefault("rationale", fallback_response["rationale"])
        parsed.setdefault("key_factors", fallback_response["key_factors"])
        return parsed
    except Exception:
        return fallback_response