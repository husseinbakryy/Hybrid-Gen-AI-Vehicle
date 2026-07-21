"""Verify that _enforce_consistency produces logically coherent outputs
for three representative scenarios: pure EV, pure ICE, and hybrid."""

import sys
from pathlib import Path

# Ensure the Models directory is on sys.path
REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_DIR = REPO_ROOT / "Models"
if str(MODELS_DIR) not in sys.path:
    sys.path.insert(0, str(MODELS_DIR))

from pipeline.inference import _enforce_consistency


def _check(label, condition, msg):
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}: {msg}")
    return condition


def test_ev_scenario():
    """Pure EV vehicle: fuel must be 0, battery capped, CO2 = battery-only."""
    print("\n=== Scenario 1: Pure EV (Tesla Model 3, 50 km trip) ===")
    raw = {
        "recommended_mode": "ev",
        "fuel_used_l": 1.5,       # model wrongly predicts fuel
        "battery_used_kwh": 8.0,
        "co2_emissions_kg": 5.0,  # model's independent prediction
        "trip_cost_usd": 3.5,     # model's independent prediction
        "range_left_km": 11.23,   # stagnant default
        "trip_time_min": 25.0,
    }
    inputs = {
        "powertrain_type": "ev",
        "usable_battery_kwh": 60.0,
        "fuel_tank_l": 0.0,
        "distance_km": 50.0,
    }

    out = _enforce_consistency(raw, inputs)
    ok = True
    ok &= _check("Fuel zeroed", out["fuel_used_l"] == 0.0,
                  f"fuel={out['fuel_used_l']}")
    ok &= _check("Battery capped", 0 < out["battery_used_kwh"] <= 60.0,
                  f"battery={out['battery_used_kwh']}")
    ok &= _check("CO2 formula", abs(out["co2_emissions_kg"] - (0.0 * 2.31 + 8.0 * 0.37)) < 0.01,
                  f"co2={out['co2_emissions_kg']}")
    ok &= _check("Cost formula", abs(out["trip_cost_usd"] - (0.0 * 1.50 + 8.0 * 0.15)) < 0.01,
                  f"cost={out['trip_cost_usd']}")
    ok &= _check("Range > 0", out["range_left_km"] > 0,
                  f"range={out['range_left_km']}")
    ok &= _check("Time >= floor", out["trip_time_min"] >= (50 / 120) * 60,
                  f"time={out['trip_time_min']}")
    ok &= _check("Mode = ev", out["recommended_mode"] == "ev",
                  f"mode={out['recommended_mode']}")
    return ok


def test_ice_scenario():
    """Pure ICE vehicle: battery must be 0, CO2 = fuel-only."""
    print("\n=== Scenario 2: Pure ICE (Ford F-150, 100 km trip) ===")
    raw = {
        "recommended_mode": "ev",     # model wrongly predicts EV for ICE
        "fuel_used_l": 8.5,
        "battery_used_kwh": 3.0,      # model wrongly predicts battery
        "co2_emissions_kg": 10.0,
        "trip_cost_usd": 7.0,
        "range_left_km": -5.0,        # negative!
        "trip_time_min": 0.5,         # below floor
    }
    inputs = {
        "powertrain_type": "ice",
        "usable_battery_kwh": 0.0,
        "fuel_tank_l": 80.0,
        "distance_km": 100.0,
    }

    out = _enforce_consistency(raw, inputs)
    ok = True
    ok &= _check("Battery zeroed", out["battery_used_kwh"] == 0.0,
                  f"battery={out['battery_used_kwh']}")
    ok &= _check("Fuel preserved", out["fuel_used_l"] == 8.5,
                  f"fuel={out['fuel_used_l']}")
    ok &= _check("CO2 fuel-only", abs(out["co2_emissions_kg"] - 8.5 * 2.31) < 0.01,
                  f"co2={out['co2_emissions_kg']}")
    ok &= _check("Cost fuel-only", abs(out["trip_cost_usd"] - 8.5 * 1.50) < 0.01,
                  f"cost={out['trip_cost_usd']}")
    ok &= _check("Range >= 0", out["range_left_km"] >= 0,
                  f"range={out['range_left_km']}")
    ok &= _check("Mode = ice", out["recommended_mode"] == "ice",
                  f"mode={out['recommended_mode']}")
    ok &= _check("Time >= floor", out["trip_time_min"] >= (100 / 120) * 60,
                  f"time={out['trip_time_min']}")
    return ok


def test_hybrid_scenario():
    """Hybrid vehicle: both energy types OK, mode override if distance > EV range."""
    print("\n=== Scenario 3: Hybrid (Toyota Camry, 200 km trip, model predicts EV) ===")
    raw = {
        "recommended_mode": "ev",     # should be overridden — 200 km > 50 km EV range
        "fuel_used_l": 5.0,
        "battery_used_kwh": 6.0,
        "co2_emissions_kg": 15.0,
        "trip_cost_usd": 10.0,
        "range_left_km": 11.23,
        "trip_time_min": -2.0,        # negative!
    }
    inputs = {
        "powertrain_type": "hybrid",
        "usable_battery_kwh": 8.0,    # small battery → EV range = 8/0.16 = 50 km
        "fuel_tank_l": 50.0,
        "distance_km": 200.0,
    }

    out = _enforce_consistency(raw, inputs)
    ok = True
    ok &= _check("Mode overridden to hybrid", out["recommended_mode"] == "hybrid",
                  f"mode={out['recommended_mode']}")
    ok &= _check("Fuel > 0 (hybrid)", out["fuel_used_l"] > 0,
                  f"fuel={out['fuel_used_l']}")
    ok &= _check("Battery capped to capacity", out["battery_used_kwh"] <= 8.0,
                  f"battery={out['battery_used_kwh']}")
    expected_co2 = out["fuel_used_l"] * 2.31 + out["battery_used_kwh"] * 0.37
    ok &= _check("CO2 matches formula", abs(out["co2_emissions_kg"] - expected_co2) < 0.01,
                  f"co2={out['co2_emissions_kg']} expected={expected_co2:.4f}")
    expected_cost = out["fuel_used_l"] * 1.50 + out["battery_used_kwh"] * 0.15
    ok &= _check("Cost matches formula", abs(out["trip_cost_usd"] - expected_cost) < 0.01,
                  f"cost={out['trip_cost_usd']} expected={expected_cost:.4f}")
    ok &= _check("Range > 0", out["range_left_km"] > 0,
                  f"range={out['range_left_km']}")
    ok &= _check("Time >= 1 min (was negative)", out["trip_time_min"] >= 1.0,
                  f"time={out['trip_time_min']}")
    ok &= _check("No negatives", all(
        out[k] >= 0 for k in ("fuel_used_l", "battery_used_kwh",
                               "co2_emissions_kg", "trip_cost_usd",
                               "range_left_km", "trip_time_min")),
                  "all numeric targets >= 0")
    return ok


if __name__ == "__main__":
    results = [test_ev_scenario(), test_ice_scenario(), test_hybrid_scenario()]
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Scenarios passed: {passed}/{total}")
    if all(results):
        print("ALL SCENARIOS PASSED")
    else:
        print("SOME SCENARIOS FAILED")
        sys.exit(1)
