import openai

from recommender import generate_recommendation


def test_generate_recommendation_falls_back_when_openai_is_unreachable(monkeypatch):
    class FakeCompletions:
        def create(self, *args, **kwargs):
            raise openai.APIConnectionError(request=None)

    monkeypatch.setattr("recommender.client", type("Client", (), {"chat": type("Chat", (), {"completions": FakeCompletions()})})())

    result = generate_recommendation(
        trip_input={"distance_km": 12, "battery_soc_start": 80, "road_type": "urban", "traffic_level": "low"},
        ml_output={"recommended_mode": "ev", "cost": 1.5},
        user_context={"comfort_priority": "balanced"},
    )

    assert isinstance(result, dict)
    assert "recommendation" in result
    assert result["recommended_mode"] == "ev"
