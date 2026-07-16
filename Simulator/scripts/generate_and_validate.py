"""Generate a benchmark dataset, run diagnostics, and save validation artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from simulator.diagnostics import run_diagnostics
from simulator.trip_sampler import TripSimulator


def main() -> None:
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    simulator = TripSimulator(seed=42)
    dataset = simulator.generate_trips(n_trips=20_000, n_drivers=500)
    dataset_path = artifacts_dir / "synthetic_trips_20k.csv"
    diagnostics_path = artifacts_dir / "diagnostics_summary.json"
    plots_dir = artifacts_dir / "validation_plots"

    dataset.to_csv(dataset_path, index=False)
    diagnostics = run_diagnostics(dataset, verbose=True, save_json_path=diagnostics_path, plot_dir=plots_dir)

    with (artifacts_dir / "generation_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "seed": 42,
                "n_rows": int(len(dataset)),
                "dataset_path": str(dataset_path),
                "diagnostics_path": str(diagnostics_path),
                "plots_dir": str(plots_dir),
            },
            handle,
            indent=2,
        )

    print(f"Saved dataset to {dataset_path}")
    print(f"Saved diagnostics to {diagnostics_path}")
    print(f"Saved plots to {plots_dir}")


if __name__ == "__main__":
    main()
