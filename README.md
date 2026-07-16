# Hybrid-Gen-AI-Vehicle

Hybrid-Gen-AI-Vehicle combines a synthetic trip simulator with an interactive dashboard for exploring mobility and recommendation scenarios.

## Repository Structure

- `Simulator/`: Python package for synthetic trip generation, diagnostics, labeling, and ML prep.
- `Dashboard/`: PyQt-based UI for trip setup, mode recommendations, and visual summaries.
- `Backend/`: Reserved for service/API layer (currently empty).
- `Data/`: Shared datasets (currently includes `synthetic_trips.csv`).
- `Models/`: Modular training and inference pipeline for five prediction models.

## Prerequisites

- Python 3.10+ for `Simulator/`
- Python 3.14+ for `Dashboard/` (as currently declared)
- `uv` installed (recommended): https://docs.astral.sh/uv/

## Quick Start

### 1) Run the Dashboard

```powershell
cd Dashboard
uv sync
uv run python main.py
```

### 2) Run the Simulator Script

```powershell
cd Simulator
uv sync
uv run python scripts/generate_and_validate.py
```

### 3) Run Simulator Tests

```powershell
cd Simulator
uv run pytest -q
```

### 4) Run the Models Pipeline

```powershell
cd Models
uv sync
uv run python synthetic_trip_capgemini.py
```

## Simulator Notes

- Main package source is under `Simulator/simulator/`.
- Tests are under `Simulator/tests/`.
- Generated files are written to `Simulator/artifacts/`.
- `Simulator/.gitignore` is configured to ignore generated outputs and local dev artifacts.

## Dashboard Notes

- Main entry point is `Dashboard/main.py`.
- UI components live under `Dashboard/widgets/`.
- `Dashboard/.gitignore` is configured for Python and local environment artifacts.

## Models Notes

- Dataset is loaded from `Data/synthetic_trips.csv` by default.
- Pipeline modules are under `Models/pipeline/` with one trainer file per model.
- Trained artifacts are written to `Models/artifacts/`.
- `Models/.gitignore` is configured to ignore generated artifacts and local files.

## Recommended Next Steps

1. Add a backend service in `Backend/` for model-serving endpoints.
2. Define dataset contracts in `Data/` and keep large raw data out of git.
3. Version trained artifacts in `Models/` with metadata for reproducibility.
