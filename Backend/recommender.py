from __future__ import annotations
 
import json
import os
from typing import Any
from urllib import error, request
 
from dotenv import load_dotenv
 
load_dotenv(override=True)
 
OPENROUTER_CHAT_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o")
 
def build_agent_prompt(user_input: dict[str, Any], vehicle_data: dict[str, Any], ml_metrics: dict[str, Any]) -> str:
    return (
        "You are an expert Autonomous Vehicle Recommender Agent. "
        "Your task is to analyze the user's trip goals, the selected vehicle's database specifications, "
        "and the machine learning predictive outputs to formulate an optimized trip plan.\n\n"
        f"1. User Trip Input: {json.dumps(user_input, default=str)}\n"
        f"2. Vehicle Database Specs: {json.dumps(vehicle_data, default=str)}\n"
        f"3. ML Pipeline Metrics: {json.dumps(ml_metrics, default=str)}\n\n"
        "Return a strict JSON object with these exact keys: "
        "'summary', 'suggested_mode', 'actions', 'confidence', 'rationale', 'key_factors'. "
        "Ensure summary references specific vehicle names and metrics."
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
 
def run_recommender_agent(user_input: dict[str, Any], vehicle_data: dict[str, Any], ml_metrics: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    fallback_mode = str(ml_metrics.get("recommended_mode", "hybrid")).lower()
    
    fallback_response = {
        "summary": f"Driving a {vehicle_data.get('vehicle_name', 'Vehicle')} for this trip yields an estimated cost of ${ml_metrics.get('trip_cost_usd', 0.0):.2f}. Utilizing {fallback_mode.upper()} mode is optimal for efficiency.",
        "suggested_mode": fallback_mode,
        "actions": [
            "Monitor battery state of charge (SoC) during highway segments.",
            "Engage regenerative braking descending slopes.",
            "Keep HVAC levels balanced to preserve range."
        ],
        "confidence": "high",
        "rationale": "Heuristic fallback generated successfully via database and ML integration.",
        "key_factors": ["distance_km", "powertrain_type", "nominalEvRangeKm"]
    }
 
    if not api_key:
        return fallback_response
 
    prompt = build_agent_prompt(user_input, vehicle_data, ml_metrics)
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
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
        parsed.setdefault("suggested_mode", fallback_mode)
        parsed.setdefault("summary", fallback_response["summary"])
        parsed.setdefault("actions", fallback_response["actions"])
        parsed.setdefault("confidence", "high")
        parsed.setdefault("rationale", "")
        parsed.setdefault("key_factors", [])
        return parsed
    except Exception:
        return fallback_response