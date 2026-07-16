"""Trip purpose priors and samplers."""

from __future__ import annotations

import numpy as np

from .entities import TripPurposeProfile


PURPOSE_PROFILES: dict[str, TripPurposeProfile] = {
    "commute": TripPurposeProfile(
        purpose="commute",
        distance_mean_km=18.0,
        distance_std_km=9.5,
        departure_hour_mean=8.0,
        departure_hour_std=1.4,
        road_mix={"urban": 0.48, "arterial": 0.24, "suburban": 0.16, "highway": 0.12},
        passenger_mean=1.0,
        passenger_std=0.2,
        cargo_mean_kg=4.0,
        cargo_std_kg=2.5,
        urgency_prior=0.84,
        weekday_preference=0.96,
        weekend_preference=0.08,
    ),
    "errand": TripPurposeProfile(
        purpose="errand",
        distance_mean_km=7.5,
        distance_std_km=4.5,
        departure_hour_mean=13.0,
        departure_hour_std=3.0,
        road_mix={"urban": 0.60, "arterial": 0.24, "suburban": 0.12, "highway": 0.04},
        passenger_mean=1.4,
        passenger_std=0.6,
        cargo_mean_kg=13.0,
        cargo_std_kg=6.0,
        urgency_prior=0.43,
        weekday_preference=0.56,
        weekend_preference=0.62,
    ),
    "school_run": TripPurposeProfile(
        purpose="school_run",
        distance_mean_km=10.0,
        distance_std_km=5.0,
        departure_hour_mean=7.4,
        departure_hour_std=0.9,
        road_mix={"urban": 0.56, "arterial": 0.24, "suburban": 0.16, "highway": 0.04},
        passenger_mean=2.0,
        passenger_std=0.8,
        cargo_mean_kg=7.0,
        cargo_std_kg=4.0,
        urgency_prior=0.72,
        weekday_preference=0.92,
        weekend_preference=0.10,
    ),
    "leisure": TripPurposeProfile(
        purpose="leisure",
        distance_mean_km=24.0,
        distance_std_km=13.0,
        departure_hour_mean=15.0,
        departure_hour_std=3.5,
        road_mix={"urban": 0.28, "arterial": 0.22, "suburban": 0.22, "highway": 0.28},
        passenger_mean=2.2,
        passenger_std=1.0,
        cargo_mean_kg=18.0,
        cargo_std_kg=9.0,
        urgency_prior=0.28,
        weekday_preference=0.35,
        weekend_preference=0.82,
    ),
    "airport": TripPurposeProfile(
        purpose="airport",
        distance_mean_km=31.0,
        distance_std_km=16.0,
        departure_hour_mean=10.0,
        departure_hour_std=4.2,
        road_mix={"urban": 0.20, "arterial": 0.18, "suburban": 0.22, "highway": 0.40},
        passenger_mean=1.6,
        passenger_std=0.9,
        cargo_mean_kg=38.0,
        cargo_std_kg=18.0,
        urgency_prior=0.78,
        weekday_preference=0.66,
        weekend_preference=0.54,
    ),
    "road_trip": TripPurposeProfile(
        purpose="road_trip",
        distance_mean_km=156.0,
        distance_std_km=78.0,
        departure_hour_mean=9.0,
        departure_hour_std=2.5,
        road_mix={"urban": 0.08, "arterial": 0.12, "suburban": 0.20, "highway": 0.60},
        passenger_mean=2.8,
        passenger_std=1.1,
        cargo_mean_kg=62.0,
        cargo_std_kg=25.0,
        urgency_prior=0.16,
        weekday_preference=0.18,
        weekend_preference=0.82,
    ),
    "business": TripPurposeProfile(
        purpose="business",
        distance_mean_km=21.0,
        distance_std_km=11.0,
        departure_hour_mean=9.5,
        departure_hour_std=2.3,
        road_mix={"urban": 0.36, "arterial": 0.24, "suburban": 0.18, "highway": 0.22},
        passenger_mean=1.1,
        passenger_std=0.4,
        cargo_mean_kg=15.0,
        cargo_std_kg=8.0,
        urgency_prior=0.64,
        weekday_preference=0.88,
        weekend_preference=0.22,
    ),
}

PURPOSE_WEIGHTS = np.array([0.26, 0.18, 0.10, 0.18, 0.08, 0.10, 0.10])
PURPOSE_ORDER = list(PURPOSE_PROFILES.keys())


def _bounded_normal(rng: np.random.Generator, mean: float, std: float, lower: float, upper: float) -> float:
    return float(np.clip(rng.normal(mean, std), lower, upper))


def choose_trip_purpose(rng: np.random.Generator, preferred_purposes: list[str], day_type: str) -> str:
    if preferred_purposes:
        weights = PURPOSE_WEIGHTS.copy()
        for purpose in preferred_purposes:
            if purpose in PURPOSE_ORDER:
                weights[PURPOSE_ORDER.index(purpose)] *= 1.45
        if day_type == "weekday":
            weights[PURPOSE_ORDER.index("commute")] *= 1.5
            weights[PURPOSE_ORDER.index("business")] *= 1.2
        else:
            weights[PURPOSE_ORDER.index("leisure")] *= 1.7
            weights[PURPOSE_ORDER.index("road_trip")] *= 1.55
            weights[PURPOSE_ORDER.index("errand")] *= 1.1
        weights = weights / weights.sum()
        return str(rng.choice(PURPOSE_ORDER, p=weights))
    return str(rng.choice(PURPOSE_ORDER, p=PURPOSE_WEIGHTS))


def sample_trip_purpose_context(rng: np.random.Generator, purpose: str, day_type: str) -> dict:
    profile = PURPOSE_PROFILES[purpose]
    distance_km = max(1.0, _bounded_normal(rng, profile.distance_mean_km, profile.distance_std_km, 1.0, 650.0))
    departure_hour = int(np.round(_bounded_normal(rng, profile.departure_hour_mean, profile.departure_hour_std, 0.0, 23.0)))
    road_types = list(profile.road_mix.keys())
    road_probs = np.array(list(profile.road_mix.values()), dtype=float)
    road_probs = road_probs / road_probs.sum()
    road_type = str(rng.choice(road_types, p=road_probs))
    passengers = int(max(1, np.round(_bounded_normal(rng, profile.passenger_mean, profile.passenger_std, 1.0, 6.0))))
    cargo_kg = float(max(0.0, _bounded_normal(rng, profile.cargo_mean_kg, profile.cargo_std_kg, 0.0, 220.0)))
    return {
        "trip_purpose": purpose,
        "distance_km": distance_km,
        "departure_hour": departure_hour,
        "road_type": road_type,
        "passengers": passengers,
        "cargo_kg": cargo_kg,
        "urgency_prior": profile.urgency_prior,
        "day_preference": profile.weekday_preference if day_type == "weekday" else profile.weekend_preference,
    }
