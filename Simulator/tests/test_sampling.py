from simulator.trip_sampler import TripSimulator


def test_reproducible_trip_generation():
    sim_a = TripSimulator(seed=123)
    sim_b = TripSimulator(seed=123)
    df_a = sim_a.generate_trips(n_trips=120, n_drivers=24)
    df_b = sim_b.generate_trips(n_trips=120, n_drivers=24)
    assert df_a.equals(df_b)


def test_persistent_entities_and_variety():
    sim = TripSimulator(seed=7)
    df = sim.generate_trips(n_trips=200, n_drivers=40)
    assert df["driver_id"].nunique() > 10
    assert df["vehicle_id"].nunique() > 3
    assert df["trip_purpose"].nunique() >= 4
    assert df["true_duration_min"].gt(0).all()
