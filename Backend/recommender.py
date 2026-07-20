from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

from dotenv import load_dotenv


load_dotenv(override=True)

OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")


def _build_prompt(trip_input: dict[str, Any], ml_output: dict[str, Any], user_context: dict[str, Any]) -> str:
    return (
        "You are a concise driving recommendation assistant for a hybrid/EV vehicle app. "
        "Use the provided ML outputs and user context to produce practical guidance. "
        "Return JSON only with these keys: summary, suggested_mode, actions, confidence, rationale, key_factors, source. "
        "Rules: summary should be 2-4 sentences; suggested_mode must be one of ev, hybrid, or ice; "
        "actions must be a short array of actionable bullets; confidence must be low, medium, or high; "
        "key_factors should mention the inputs that mattered most; source should identify the model used.\n\n"
        f"Trip input: {json.dumps(trip_input, ensure_ascii=True, default=str)}\n"
        f"ML output: {json.dumps(ml_output, ensure_ascii=True, default=str)}\n"
        f"User context: {json.dumps(user_context, ensure_ascii=True, default=str)}"
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


def _local_fallback(trip_input: dict[str, Any], ml_output: dict[str, Any], user_context: dict[str, Any]) -> dict[str, Any]:
    mode = str(ml_output.get("recommended_mode", "hybrid")).lower()
    distance = float(trip_input.get("distance_km", 0.0))
    passengers = int(trip_input.get("passengers", 1))
    cost = float(ml_output.get("trip_cost_usd", 0.0))
    co2 = float(ml_output.get("co2_emissions_kg", 0.0))
    comfort_pref = user_context.get("comfort_priority")

    if mode == "ev":
        primary_tip = "Prefer EV mode for this trip to reduce operating cost and emissions."
    elif mode == "hybrid":
        primary_tip = "Use hybrid mode and smooth out acceleration in stop-and-go segments."
    else:
        primary_tip = "Use efficient ICE driving with gentle acceleration and minimal idling."

    comfort_line = (
        f"Comfort priority is set to '{comfort_pref}', so balance HVAC and throttle response."
        if comfort_pref
        else "If comfort matters, keep HVAC changes gradual to avoid energy spikes."
    )

    return {
        "summary": (
            f"Trip distance is {distance:.1f} km with {passengers} passenger(s). "
            f"Predicted cost is ${cost:.2f} and CO2 is {co2:.2f} kg. "
            f"{primary_tip} {comfort_line}"
        ),
        "suggested_mode": mode,
        "actions": [
            "Avoid rapid acceleration in dense traffic.",
            "Plan a route with fewer stop-and-go segments where possible.",
            "Monitor HVAC usage when ambient conditions are mild.",
        ],
        "confidence": "medium",
        "rationale": "Fallback guidance generated locally because the GenAI request was unavailable.",
        "key_factors": ["distance_km", "passengers", "recommended_mode", "trip_cost_usd", "co2_emissions_kg"],
        "source": "local-fallback",
    }


def _call_openrouter(prompt: str) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
    }

    req = request.Request(
        OPENROUTER_CHAT_COMPLETIONS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Hybrid-Gen-AI-Vehicle"),
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=30) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenRouter request failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"OpenRouter request failed: {exc.reason}") from exc

    choices = response_payload.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter response did not include any choices.")

    message = choices[0].get("message", {})
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("OpenRouter response did not include message content.")

    parsed = _extract_json(content)
    parsed.setdefault("source", f"openrouter:{DEFAULT_MODEL}")
    return parsed


def generate_recommendation(
    trip_input: dict[str, Any],
    ml_output: dict[str, Any],
    user_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_context = user_context or {}
    prompt = _build_prompt(trip_input, ml_output, user_context)

    try:
        recommendation = _call_openrouter(prompt)
    except Exception:
        recommendation = _local_fallback(trip_input, ml_output, user_context)

    recommendation.setdefault("suggested_mode", str(ml_output.get("recommended_mode", "hybrid")).lower())
    recommendation.setdefault("summary", "No summary returned by the model.")
    recommendation.setdefault("actions", [])
    recommendation.setdefault("confidence", "medium")
    recommendation.setdefault("rationale", "")
    recommendation.setdefault("key_factors", [])
    recommendation.setdefault("source", f"openrouter:{DEFAULT_MODEL}")

    return recommendation
