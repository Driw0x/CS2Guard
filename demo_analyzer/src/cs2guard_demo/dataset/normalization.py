import math

import pandas as pd


AIM_FEATURE_COLUMNS = [
    "mean_angular_speed",
    "max_angular_speed",
    "std_angular_speed",
    "mean_angular_acceleration",
    "max_angular_acceleration",
    "std_angular_acceleration",
]


def fit_normalization_stats(dataset: pd.DataFrame, columns: list[str]) -> dict[str, dict[str, float]]:
    if dataset.empty:
        raise ValueError("Cannot fit normalization on an empty dataset.")

    missing_columns = [column for column in columns if column not in dataset.columns]

    if missing_columns:
        raise ValueError(f"Missing normalization columns: {missing_columns}")

    stats = {}

    for column in columns:
        values = pd.to_numeric(dataset[column], errors="coerce")

        if values.isna().any():
            raise ValueError(f"Column '{column}' contains invalid values.")

        mean = float(values.mean())
        std = float(values.std(ddof=0))

        if not math.isfinite(mean) or not math.isfinite(std):
            raise ValueError(f"Column '{column}' contains non-finite values.")

        stats[column] = {
            "mean": mean,
            "std": std,
        }

    return stats


def normalize_features(dataset: pd.DataFrame, stats: dict[str, dict[str, float]]) -> pd.DataFrame:
    normalized = dataset.copy()

    for column, column_stats in stats.items():
        if column not in normalized.columns:
            raise ValueError(f"Missing normalization column: {column}")

        mean = column_stats["mean"]
        std = column_stats["std"]

        if std == 0.0:
            normalized[column] = 0.0
        else:
            normalized[column] = (normalized[column] - mean) / std

    return normalized