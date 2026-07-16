"""Dataset diagnostics for realism, dependencies, and non-triviality."""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


NUMERIC_DIAGNOSTIC_COLUMNS = [
    "distance_km",
    "true_duration_min",
    "true_avg_speed_kmh",
    "true_battery_used_kwh",
    "true_fuel_used_l",
    "ambient_temp_c",
    "true_stop_count",
    "cargo_kg",
    "passengers",
    "true_battery_soc_start_pct",
    "true_battery_soc_end_pct",
]


def _safe_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[column], errors="coerce")


def basic_diagnostics(df: pd.DataFrame) -> dict[str, Any]:
    mode_counts = df["recommended_mode"].value_counts(dropna=False).to_dict() if "recommended_mode" in df.columns else {}
    mode_share = {key: float(value / max(len(df), 1)) for key, value in mode_counts.items()}
    return {
        "n_trips": int(len(df)),
        "n_drivers": int(df["driver_id"].nunique()) if "driver_id" in df.columns else 0,
        "n_vehicles": int(df["vehicle_id"].nunique()) if "vehicle_id" in df.columns else 0,
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_trip_ids": int(df["trip_id"].duplicated().sum()) if "trip_id" in df.columns else 0,
        "duplicate_rows": int(df.duplicated().sum()),
        "recommended_mode_counts": mode_counts,
        "recommended_mode_share": mode_share,
    }


def distribution_diagnostics(df: pd.DataFrame, columns: list[str] | None = None) -> dict[str, dict[str, float]]:
    columns = columns or NUMERIC_DIAGNOSTIC_COLUMNS
    summary: dict[str, dict[str, float]] = {}
    for column in columns:
        series = _safe_series(df, column).dropna()
        if series.empty:
            continue
        summary[column] = {
            "mean": float(series.mean()),
            "std": float(series.std(ddof=0)),
            "min": float(series.min()),
            "p05": float(series.quantile(0.05)),
            "p25": float(series.quantile(0.25)),
            "p50": float(series.quantile(0.50)),
            "p75": float(series.quantile(0.75)),
            "p95": float(series.quantile(0.95)),
            "max": float(series.max()),
        }
    return summary


def _pearson(df: pd.DataFrame, left: str, right: str) -> float:
    if left not in df.columns or right not in df.columns:
        return float("nan")
    x = pd.to_numeric(df[left], errors="coerce")
    y = pd.to_numeric(df[right], errors="coerce")
    valid = x.notna() & y.notna()
    if valid.sum() < 3:
        return float("nan")
    return float(x[valid].corr(y[valid]))


def _entropy(values: pd.Series) -> float:
    probs = values.value_counts(normalize=True, dropna=False)
    probs = probs[probs > 0]
    return float(-(probs * np.log2(probs)).sum())


def _normalized_mutual_information(x: pd.Series, y: pd.Series, bins: int = 8) -> float:
    valid = x.notna() & y.notna()
    if valid.sum() < 10:
        return float("nan")
    x_valid = x[valid]
    y_valid = y[valid].astype(str)
    try:
        x_bins = pd.qcut(x_valid.rank(method="first"), q=min(bins, max(2, x_valid.nunique())), duplicates="drop")
    except ValueError:
        x_bins = pd.cut(x_valid, bins=min(bins, max(2, x_valid.nunique())))
    contingency = pd.crosstab(x_bins, y_valid)
    total = float(contingency.to_numpy().sum())
    if total <= 0:
        return float("nan")
    px = contingency.sum(axis=1) / total
    py = contingency.sum(axis=0) / total
    mi = 0.0
    for i in contingency.index:
        for j in contingency.columns:
            joint = float(contingency.loc[i, j]) / total
            if joint <= 0:
                continue
            mi += joint * math.log2(joint / float(px.loc[i] * py.loc[j]))
    hx = _entropy(x_bins.astype(str))
    hy = _entropy(y_valid)
    denom = max(hx, hy)
    return float(mi / denom) if denom > 0 else 0.0


def _best_threshold_accuracy(values: pd.Series, labels: pd.Series, target_label: str) -> dict[str, float]:
    valid = values.notna() & labels.notna()
    values = pd.to_numeric(values[valid], errors="coerce")
    labels = labels[valid].astype(str)
    best = {"accuracy": 0.0, "direction": "lt", "threshold": float("nan")}
    if values.nunique() < 2:
        return best
    thresholds = np.unique(np.quantile(values, np.linspace(0.05, 0.95, 25)))
    binary = labels == target_label
    for threshold in thresholds:
        for direction in ("lt", "gt"):
            if direction == "lt":
                pred = values <= threshold
            else:
                pred = values >= threshold
            accuracy = float((pred == binary).mean())
            if accuracy > best["accuracy"]:
                best = {"accuracy": accuracy, "direction": direction, "threshold": float(threshold)}
    return best


def dependency_diagnostics(df: pd.DataFrame) -> dict[str, Any]:
    dependency = {
        "distance_vs_battery_used_kwh": _pearson(df, "distance_km", "true_battery_used_kwh"),
        "traffic_vs_duration_min": _pearson(df, "traffic_level", "true_duration_min"),
        "ambient_temp_vs_hvac_kw": _pearson(df, "ambient_temp_c", "true_hvac_kw"),
        "aggressiveness_vs_stop_count": _pearson(df, "aggressiveness", "true_stop_count"),
        "aggressiveness_vs_speed_variance": _pearson(df, "aggressiveness", "behavior_speed_variability"),
        "battery_health_vs_battery_used_kwh_per_km": _pearson(df.assign(battery_used_per_km=df["true_battery_used_kwh"] / df["distance_km"].clip(lower=1.0)), "battery_health", "battery_used_per_km"),
        "purpose_distance_means": df.groupby("trip_purpose")["distance_km"].mean().round(3).to_dict() if "trip_purpose" in df.columns else {},
        "purpose_departure_hour_means": df.groupby("trip_purpose")["departure_hour"].mean().round(3).to_dict() if "trip_purpose" in df.columns else {},
        "city_season_weather_table": df.groupby(["city", "season", "weather"]).size().rename("count").reset_index().to_dict(orient="records") if {"city", "season", "weather"}.issubset(df.columns) else [],
    }
    return dependency


def non_triviality_diagnostics(df: pd.DataFrame) -> dict[str, Any]:
    label = df["recommended_mode"].astype(str) if "recommended_mode" in df.columns else pd.Series(dtype=str)
    if label.empty:
        return {}
    mi_ranking = []
    for column in [
        "distance_km",
        "true_battery_soc_start_pct",
        "traffic_level",
        "ambient_temp_c",
        "true_stop_count",
        "passengers",
        "cargo_kg",
        "aggressiveness",
        "range_anxiety",
        "route_familiarity_bias",
        "true_avg_speed_kmh",
    ]:
        if column in df.columns:
            mi_ranking.append((column, _normalized_mutual_information(_safe_series(df, column), label)))
    mi_ranking.sort(key=lambda item: item[1] if not np.isnan(item[1]) else -1.0, reverse=True)

    threshold_checks = {
        "distance_km": {mode: _best_threshold_accuracy(_safe_series(df, "distance_km"), label, mode) for mode in label.unique()},
        "true_battery_soc_start_pct": {mode: _best_threshold_accuracy(_safe_series(df, "true_battery_soc_start_pct"), label, mode) for mode in label.unique()},
    }

    mode_counts = label.value_counts(normalize=True).to_dict()
    imbalance = float(max(mode_counts.values()) / max(min(mode_counts.values()), 1e-9)) if mode_counts else float("nan")
    switch_point_std = float(pd.to_numeric(df["switch_point_km"], errors="coerce").std(ddof=0)) if "switch_point_km" in df.columns else float("nan")

    return {
        "feature_mi_ranking": mi_ranking[:10],
        "threshold_checks": threshold_checks,
        "label_imbalance_ratio": imbalance,
        "switch_point_km_std": switch_point_std,
        "switch_point_km_unique": int(df["switch_point_km"].nunique()) if "switch_point_km" in df.columns else 0,
    }


def realism_sanity_checks(df: pd.DataFrame) -> dict[str, Any]:
    issues: dict[str, Any] = {}
    issues["negative_distance_rows"] = int((pd.to_numeric(df.get("distance_km"), errors="coerce") < 0).sum()) if "distance_km" in df.columns else 0
    issues["negative_duration_rows"] = int((pd.to_numeric(df.get("true_duration_min"), errors="coerce") < 0).sum()) if "true_duration_min" in df.columns else 0
    issues["speed_too_low_rows"] = int((pd.to_numeric(df.get("true_avg_speed_kmh"), errors="coerce") < 3).sum()) if "true_avg_speed_kmh" in df.columns else 0
    issues["speed_too_high_rows"] = int((pd.to_numeric(df.get("true_avg_speed_kmh"), errors="coerce") > 160).sum()) if "true_avg_speed_kmh" in df.columns else 0
    if {"true_battery_soc_start_pct", "true_battery_soc_end_pct"}.issubset(df.columns):
        start = pd.to_numeric(df["true_battery_soc_start_pct"], errors="coerce")
        end = pd.to_numeric(df["true_battery_soc_end_pct"], errors="coerce")
        used = pd.to_numeric(df.get("true_battery_used_kwh"), errors="coerce") if "true_battery_used_kwh" in df.columns else pd.Series(dtype=float)
        issues["soc_increases_without_charging"] = int(((end > start) & (used.fillna(0) > 0.001)).sum())
    issues["negative_battery_used_rows"] = int((pd.to_numeric(df.get("true_battery_used_kwh"), errors="coerce") < 0).sum()) if "true_battery_used_kwh" in df.columns else 0
    issues["negative_fuel_used_rows"] = int((pd.to_numeric(df.get("true_fuel_used_l"), errors="coerce") < 0).sum()) if "true_fuel_used_l" in df.columns else 0
    if {"passengers", "body_type"}.issubset(df.columns):
        issues["impossible_passenger_rows"] = int((pd.to_numeric(df["passengers"], errors="coerce") > 8).sum())
        issues["small_car_heavy_cargo_rows"] = int(((df["body_type"].astype(str).isin(["hatchback", "sedan"])) & (pd.to_numeric(df["cargo_kg"], errors="coerce") > 120)).sum()) if "cargo_kg" in df.columns else 0
    if {"ambient_temp_c", "true_hvac_kw"}.issubset(df.columns):
        temp = pd.to_numeric(df["ambient_temp_c"], errors="coerce")
        hvac = pd.to_numeric(df["true_hvac_kw"], errors="coerce")
        issues["extreme_temp_low_hvac_rows"] = int((((temp < 0) | (temp > 32)) & (hvac < 0.9)).sum())
    if {"weather", "precipitation_mm"}.issubset(df.columns):
        issues["rain_clear_weather_rows"] = int(((pd.to_numeric(df["precipitation_mm"], errors="coerce") > 0.25) & (df["weather"].astype(str) == "clear")).sum())
    return issues


def _maybe_warn(issues: dict[str, Any]) -> None:
    if any(value for value in issues.values() if isinstance(value, (int, float)) and value > 0):
        warnings.warn(f"Diagnostics found potential realism issues: {issues}", RuntimeWarning, stacklevel=2)


def run_diagnostics(
    df: pd.DataFrame,
    verbose: bool = True,
    save_json_path: Path | str | None = None,
    plot_dir: Path | str | None = None,
) -> dict[str, Any]:
    summary = {
        "basic": basic_diagnostics(df),
        "distribution": distribution_diagnostics(df),
        "dependencies": dependency_diagnostics(df),
        "non_triviality": non_triviality_diagnostics(df),
        "realism": realism_sanity_checks(df),
    }
    _maybe_warn(summary["realism"])

    if save_json_path is not None:
        path = Path(save_json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, default=_json_default)

    if plot_dir is not None:
        _save_plots(df, Path(plot_dir))

    if verbose:
        print(_format_summary(summary))
    return summary


def _json_default(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    return str(value)


def _format_summary(summary: dict[str, Any]) -> str:
    basic = summary["basic"]
    realism = summary["realism"]
    nontrivial = summary["non_triviality"]
    top_feature = nontrivial.get("feature_mi_ranking", [("n/a", float("nan"))])[0]
    return (
        f"Trips={basic['n_trips']}, drivers={basic['n_drivers']}, vehicles={basic['n_vehicles']}, "
        f"missing={basic['missing_values']}, duplicates={basic['duplicate_rows']}, "
        f"top_mi_feature={top_feature[0]}:{top_feature[1]:.3f}, "
        f"realism_flags={sum(v for v in realism.values() if isinstance(v, (int, float)))}"
    )


def _save_plots(df: pd.DataFrame, plot_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return

    plot_dir.mkdir(parents=True, exist_ok=True)
    if "recommended_mode" in df.columns:
        fig, ax = plt.subplots(figsize=(6, 4))
        df["recommended_mode"].value_counts().plot(kind="bar", ax=ax, color="#4C78A8")
        ax.set_title("Recommended Mode Distribution")
        ax.set_xlabel("Mode")
        ax.set_ylabel("Count")
        fig.tight_layout()
        fig.savefig(plot_dir / "recommended_mode_balance.png", dpi=150)
        plt.close(fig)

    for column in ["distance_km", "true_duration_min", "true_battery_used_kwh", "true_fuel_used_l"]:
        if column not in df.columns:
            continue
        fig, ax = plt.subplots(figsize=(6, 4))
        pd.to_numeric(df[column], errors="coerce").dropna().plot(kind="hist", bins=40, ax=ax, color="#F58518")
        ax.set_title(f"{column} Distribution")
        fig.tight_layout()
        fig.savefig(plot_dir / f"{column}_hist.png", dpi=150)
        plt.close(fig)
