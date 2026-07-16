# Models

This folder contains the modular training and inference pipeline for the hybrid trip intelligence models.

## Structure

- `synthetic_trip_capgemini.py`: Backward-compatible entry script.
- `pipeline/config.py`: Paths, feature list, targets, and model artifact names.
- `pipeline/data.py`: Dataset loading and preprocessing split logic.
- `pipeline/model_mode.py`: Recommended mode classification model.
- `pipeline/model_fuel.py`: Fuel consumption regression model.
- `pipeline/model_battery.py`: Battery usage regression model.
- `pipeline/model_emissions.py`: Emissions regression model.
- `pipeline/model_cost.py`: Trip cost regression model.
- `pipeline/inference.py`: Artifact loading and `predict_trip` inference helper.
- `pipeline/runner.py`: End-to-end training pipeline orchestrator.

## Dataset Location

The pipeline reads the dataset from:

- `../Data/synthetic_trips.csv`

## Run

```powershell
cd Models
uv sync
uv run python synthetic_trip_capgemini.py
```

## Outputs

Artifacts are written to:

- `Models/artifacts/`

Saved files include the preprocessor and all five trained model artifacts.
