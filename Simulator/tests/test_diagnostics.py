from simulator.diagnostics import run_diagnostics
from simulator.trip_sampler import TripSimulator


def test_diagnostics_return_expected_sections():
    sim = TripSimulator(seed=21)
    df = sim.generate_trips(n_trips=180, n_drivers=30)
    summary = run_diagnostics(df, verbose=False)
    assert set(summary.keys()) == {"basic", "distribution", "dependencies", "non_triviality", "realism"}
    assert summary["basic"]["n_trips"] == len(df)
    assert "recommended_mode_share" in summary["basic"]
    assert "distance_vs_battery_used_kwh" in summary["dependencies"]
