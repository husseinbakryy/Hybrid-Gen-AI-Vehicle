import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from recommender import generate_recommendation


def test_generate_recommendation_falls_back_when_openrouter_is_unreachable(monkeypatch):
    def _raise_connection_error(*args, **kwargs):
        raise RuntimeError("simulated connection failure")

    monkeypatch.setattr("recommender._call_openrouter", _raise_connection_error)

    result = generate_recommendation(
        trip_input={"distance_km": 12, "battery_soc_start": 80, "road_type": "urban", "traffic_level": "low"},
        ml_output={"recommended_mode": "ev", "trip_cost_usd": 1.5, "co2_emissions_kg": 0.8},
        user_context={"comfort_priority": "balanced"},
    )

    assert isinstance(result, dict)
    assert "summary" in result
    assert result["suggested_mode"] == "ev"
    assert result["source"] == "local-fallback"
