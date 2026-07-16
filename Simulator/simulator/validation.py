"""Validation helpers for generated datasets."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ValidationResult:
    n_rows: int
    n_drivers: int
    n_vehicles: int
    missing_values: int
    battery_nonnegative: bool
    duration_positive: bool


def validate_dataset(df: pd.DataFrame) -> ValidationResult:
    missing_values = int(df.isna().sum().sum())
    return ValidationResult(
        n_rows=int(len(df)),
        n_drivers=int(df["driver_id"].nunique()) if "driver_id" in df.columns else 0,
        n_vehicles=int(df["vehicle_id"].nunique()) if "vehicle_id" in df.columns else 0,
        missing_values=missing_values,
        battery_nonnegative=bool((df.get("true_battery_used_kwh", pd.Series(dtype=float)) >= 0).all()),
        duration_positive=bool((df.get("true_duration_min", pd.Series(dtype=float)) > 0).all()),
    )
