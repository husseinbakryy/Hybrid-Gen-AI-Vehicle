from simulator.ml_prep import build_ml_views
from simulator.trip_sampler import TripSimulator


def test_build_ml_views_excludes_obvious_leakage():
    sim = TripSimulator(seed=9)
    df = sim.generate_trips(n_trips=140, n_drivers=25)
    views = build_ml_views(df)
    assert set(views["y"].columns) == {"recommended_mode", "estimated_cost", "estimated_time_min", "battery_used_kwh", "switch_point_km"}
    assert "recommended_mode" not in views["X"].columns
    assert "true_duration_min" not in views["X"].columns
    assert "distance_km" not in views["X"].columns
    assert "base_distance_km" in views["X"].columns
    assert "recommended_mode" not in views["observed_df"].columns
