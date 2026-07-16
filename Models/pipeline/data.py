from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import DEFAULT_DATA_PATH, FEATURES, TARGET_MAP


@dataclass
class PreparedData:
    X_train_raw: pd.DataFrame
    X_test_raw: pd.DataFrame
    X_train: object
    X_test: object
    y_train: pd.DataFrame
    y_test: pd.DataFrame
    preprocessor: ColumnTransformer



def load_dataset(data_path: str | Path | None = None) -> pd.DataFrame:
    resolved_path = Path(data_path) if data_path else DEFAULT_DATA_PATH
    if not resolved_path.exists():
        raise FileNotFoundError(f"Dataset not found at {resolved_path}")

    df = pd.read_csv(resolved_path)
    required_columns = set(FEATURES + list(TARGET_MAP.values()))
    missing = sorted(required_columns - set(df.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    return df



def prepare_data(df: pd.DataFrame, test_size: float = 0.2, random_state: int = 42) -> PreparedData:
    X = df[FEATURES]
    y = df[list(TARGET_MAP.values())]

    num_cols = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
    cat_cols = X.select_dtypes(include=["object"]).columns.tolist()

    X_train_raw, X_test_raw, y_train, y_test = train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_cols),
        ]
    )

    X_train = preprocessor.fit_transform(X_train_raw)
    X_test = preprocessor.transform(X_test_raw)

    return PreparedData(
        X_train_raw=X_train_raw,
        X_test_raw=X_test_raw,
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        preprocessor=preprocessor,
    )
