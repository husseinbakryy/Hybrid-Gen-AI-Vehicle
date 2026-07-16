"""City and weather environment generation."""

from __future__ import annotations

import numpy as np

from .entities import CityProfile


CITY_PROFILES: dict[str, CityProfile] = {
    "Phoenix": CityProfile(
        city="Phoenix",
        elevation_tendency=0.16,
        urban_congestion=0.52,
        highway_congestion=0.28,
        season_temperature_c={"winter": (17.0, 5.5), "spring": (30.0, 6.5), "summer": (41.0, 5.0), "fall": (28.0, 5.5)},
        season_humidity={"winter": (0.28, 0.08), "spring": (0.20, 0.07), "summer": (0.18, 0.05), "fall": (0.22, 0.06)},
        season_precip_prob={"winter": 0.08, "spring": 0.05, "summer": 0.18, "fall": 0.06},
        season_precip_intensity_mm={"winter": (1.0, 1.5), "spring": (0.6, 1.0), "summer": (2.0, 3.5), "fall": (0.8, 1.2)},
        season_wind_kmh={"winter": (14.0, 4.0), "spring": (16.0, 5.0), "summer": (12.0, 4.0), "fall": (13.0, 4.0)},
        grid_emissions_kg_per_kwh=0.44,
        electricity_price_per_kwh=0.18,
        fuel_price_per_l=1.22,
    ),
    "Atlanta": CityProfile(
        city="Atlanta",
        elevation_tendency=0.20,
        urban_congestion=0.73,
        highway_congestion=0.44,
        season_temperature_c={"winter": (11.0, 5.0), "spring": (22.0, 6.0), "summer": (32.0, 4.5), "fall": (21.0, 5.0)},
        season_humidity={"winter": (0.54, 0.10), "spring": (0.62, 0.11), "summer": (0.71, 0.09), "fall": (0.57, 0.10)},
        season_precip_prob={"winter": 0.19, "spring": 0.31, "summer": 0.41, "fall": 0.24},
        season_precip_intensity_mm={"winter": (1.8, 2.6), "spring": (3.5, 4.2), "summer": (4.0, 5.5), "fall": (2.6, 3.4)},
        season_wind_kmh={"winter": (12.0, 4.0), "spring": (14.0, 4.5), "summer": (11.0, 3.5), "fall": (11.5, 3.5)},
        grid_emissions_kg_per_kwh=0.40,
        electricity_price_per_kwh=0.17,
        fuel_price_per_l=1.28,
    ),
    "Seattle": CityProfile(
        city="Seattle",
        elevation_tendency=0.12,
        urban_congestion=0.68,
        highway_congestion=0.40,
        season_temperature_c={"winter": (6.0, 3.5), "spring": (12.0, 4.0), "summer": (22.0, 3.5), "fall": (13.0, 3.5)},
        season_humidity={"winter": (0.78, 0.08), "spring": (0.72, 0.08), "summer": (0.66, 0.07), "fall": (0.77, 0.08)},
        season_precip_prob={"winter": 0.62, "spring": 0.48, "summer": 0.22, "fall": 0.55},
        season_precip_intensity_mm={"winter": (4.0, 5.5), "spring": (3.2, 4.2), "summer": (1.4, 2.2), "fall": (4.2, 5.0)},
        season_wind_kmh={"winter": (17.0, 5.0), "spring": (15.0, 4.5), "summer": (12.0, 3.5), "fall": (16.0, 4.5)},
        grid_emissions_kg_per_kwh=0.12,
        electricity_price_per_kwh=0.21,
        fuel_price_per_l=1.34,
    ),
    "Denver": CityProfile(
        city="Denver",
        elevation_tendency=0.68,
        urban_congestion=0.56,
        highway_congestion=0.31,
        season_temperature_c={"winter": (1.0, 6.0), "spring": (14.0, 6.5), "summer": (28.0, 5.0), "fall": (15.0, 5.5)},
        season_humidity={"winter": (0.34, 0.08), "spring": (0.32, 0.09), "summer": (0.28, 0.08), "fall": (0.30, 0.08)},
        season_precip_prob={"winter": 0.20, "spring": 0.28, "summer": 0.22, "fall": 0.18},
        season_precip_intensity_mm={"winter": (1.8, 2.8), "spring": (2.4, 3.5), "summer": (1.7, 2.5), "fall": (1.4, 2.0)},
        season_wind_kmh={"winter": (18.0, 5.0), "spring": (17.0, 4.5), "summer": (14.0, 4.0), "fall": (15.0, 4.0)},
        grid_emissions_kg_per_kwh=0.29,
        electricity_price_per_kwh=0.19,
        fuel_price_per_l=1.30,
    ),
    "Chicago": CityProfile(
        city="Chicago",
        elevation_tendency=0.18,
        urban_congestion=0.81,
        highway_congestion=0.52,
        season_temperature_c={"winter": (-4.0, 6.5), "spring": (11.0, 5.5), "summer": (25.0, 4.5), "fall": (13.0, 5.0)},
        season_humidity={"winter": (0.67, 0.09), "spring": (0.61, 0.09), "summer": (0.68, 0.08), "fall": (0.64, 0.09)},
        season_precip_prob={"winter": 0.34, "spring": 0.36, "summer": 0.30, "fall": 0.32},
        season_precip_intensity_mm={"winter": (2.4, 3.4), "spring": (3.0, 4.0), "summer": (3.0, 3.8), "fall": (2.8, 3.4)},
        season_wind_kmh={"winter": (19.0, 5.0), "spring": (17.0, 4.5), "summer": (14.0, 4.0), "fall": (18.0, 4.5)},
        grid_emissions_kg_per_kwh=0.42,
        electricity_price_per_kwh=0.20,
        fuel_price_per_l=1.33,
    ),
}

SEASONS = ("winter", "spring", "summer", "fall")


def _bounded_normal(rng: np.random.Generator, mean: float, std: float, lower: float, upper: float) -> float:
    return float(np.clip(rng.normal(mean, std), lower, upper))


def _sample_weather(rng: np.random.Generator, temp_c: float, precip_mm: float, humidity: float, wind_kmh: float) -> str:
    if precip_mm > 5.5 and temp_c <= 1.5:
        return "snow"
    if precip_mm > 7.0:
        return "heavy_rain"
    if precip_mm > 1.0:
        return "light_rain"
    if humidity > 0.75:
        return "foggy" if wind_kmh < 12.0 else "cloudy"
    if wind_kmh > 22.0:
        return "windy"
    if rng.random() < 0.35:
        return "clear"
    return "cloudy"


def sample_environment(
    rng: np.random.Generator,
    city: str,
    season: str,
    departure_hour: int,
    day_type: str,
    road_type: str,
    trip_purpose: str,
    distance_km: float,
) -> dict:
    """Sample a trip environment conditioned on city, season, hour, and trip characteristics."""

    profile = CITY_PROFILES[city]
    temp_mean, temp_std = profile.season_temperature_c[season]
    humidity_mean, humidity_std = profile.season_humidity[season]
    precip_prob = profile.season_precip_prob[season]
    precip_mean, precip_std = profile.season_precip_intensity_mm[season]
    wind_mean, wind_std = profile.season_wind_kmh[season]

    ambient_temp_c = _bounded_normal(rng, temp_mean, temp_std, -15.0, 48.0)
    humidity = _bounded_normal(rng, humidity_mean, humidity_std, 0.05, 0.99)
    precip_mm = float(max(0.0, rng.lognormal(np.log(max(0.2, precip_mean)), 0.35) - precip_mean * 0.55)) if rng.random() < precip_prob else 0.0
    wind_speed_kmh = _bounded_normal(rng, wind_mean, wind_std, 0.0, 55.0)

    if trip_purpose == "airport":
        road_bias = 0.15
    elif trip_purpose == "road_trip":
        road_bias = 0.45
    elif trip_purpose == "commute":
        road_bias = 0.30
    else:
        road_bias = 0.22

    hour_peak = np.exp(-((departure_hour - 8.0) ** 2) / 18.0) + np.exp(-((departure_hour - 17.0) ** 2) / 20.0)
    hour_peak = float(np.clip(hour_peak / 2.0, 0.0, 1.0))
    road_factor = {"urban": 1.0, "arterial": 0.8, "suburban": 0.55, "highway": 0.35}[road_type]
    congestion_base = profile.urban_congestion * road_factor + profile.highway_congestion * (1.0 - road_factor)
    traffic_level = float(np.clip(congestion_base + 0.26 * hour_peak + 0.10 * (day_type == "weekday") + 0.06 * road_bias + rng.normal(0, 0.06), 0.0, 1.0))
    expected_congestion = float(np.clip(traffic_level + rng.normal(0, 0.07), 0.0, 1.0))
    elevation_gain_m = float(max(0.0, distance_km * 1000.0 * (0.02 + profile.elevation_tendency * 0.04) + rng.normal(0.0, distance_km * 4.0)))
    elevation_loss_m = float(max(0.0, distance_km * 1000.0 * (0.015 + profile.elevation_tendency * 0.03) + rng.normal(0.0, distance_km * 3.0)))

    weather = _sample_weather(rng, ambient_temp_c, precip_mm, humidity, wind_speed_kmh)
    return {
        "weather": weather,
        "ambient_temp_c": ambient_temp_c,
        "humidity": humidity,
        "wind_speed_kmh": wind_speed_kmh,
        "precipitation_mm": precip_mm,
        "traffic_level": traffic_level,
        "expected_congestion": expected_congestion,
        "elevation_gain_m": elevation_gain_m,
        "elevation_loss_m": elevation_loss_m,
    }
