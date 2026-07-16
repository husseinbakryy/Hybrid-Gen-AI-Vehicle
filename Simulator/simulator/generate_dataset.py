"""Command-line entry point for dataset generation."""

from __future__ import annotations

import argparse
from pathlib import Path

from .trip_sampler import TripSimulator


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a stochastic synthetic trip dataset.")
    parser.add_argument("--trips", type=int, default=5000)
    parser.add_argument("--drivers", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("synthetic_trips.csv"))
    args = parser.parse_args()

    simulator = TripSimulator(seed=args.seed)
    dataset = simulator.generate_trips(n_trips=args.trips, n_drivers=args.drivers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(args.output, index=False)
    print(f"Saved {len(dataset)} rows to {args.output}")


if __name__ == "__main__":
    main()
