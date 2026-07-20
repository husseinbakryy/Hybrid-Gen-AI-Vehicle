import os
import json
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError


print("DEBUG: Loading .env...")
loaded = load_dotenv(override=True)
print(f"DEBUG: .env file found and loaded: {loaded}")

api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print("DEBUG: API Key found! Length:", len(api_key))
else:
    print("DEBUG: ERROR - API Key is empty!")

client = OpenAI(api_key=api_key) if api_key else None


def _build_local_fallback(trip_input: Dict[str, Any], ml_output: Dict[str, Any], user_context: Dict[str, Any] | None) -> Dict[str, Any]:
    recommended_mode = ml_output.get("recommended_mode", "ev")
    comfort_priority = (user_context or {}).get("comfort_priority", "balanced")
    distance_km = trip_input.get("distance_km", 0)
    traffic_level = trip_input.get("traffic_level", "normal")

    if recommended_mode == "hybrid":
        recommendation = (
            f"Use a hybrid mode for a {distance_km} km trip with {traffic_level} traffic; "
            "this balances efficiency and comfort for a balanced driver profile."
        )
    else:
        recommendation = (
            f"Use electric mode for a {distance_km} km trip with {traffic_level} traffic; "
            f"this supports lower energy use and a smooth {comfort_priority} ride."
        )

    return {
        "recommendation": recommendation,
        "recommended_mode": recommended_mode,
        "reason": "Local fallback recommendation generated because the OpenAI endpoint was unavailable.",
        "confidence": "medium",
    }


def generate_recommendation(trip_input: dict, ml_output: dict, user_context: dict = None) -> dict:
    print("DEBUG: Calling OpenAI API...")

    if not client:
        return _build_local_fallback(trip_input, ml_output, user_context)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise vehicle trip recommendation assistant. Return valid JSON only.",
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "trip_input": trip_input,
                            "ml_output": ml_output,
                            "user_context": user_context or {},
                        }
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if isinstance(content, str):
            return json.loads(content)
        return dict(content)
    except APIConnectionError as exc:
        print(f"DEBUG: OpenAI API connection failed: {exc}")
        return _build_local_fallback(trip_input, ml_output, user_context)
    except Exception as exc:
        print(f"DEBUG: OpenAI API unexpected failure: {exc}")
        return _build_local_fallback(trip_input, ml_output, user_context)