import pandas as pd

from cs2guard_demo.dataset.schema import AIM_FEATURE_COLUMNS, VALID_LABELS, validate_aim_feature_schema
from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS, prepare_features


def build_labeled_dataset(df: pd.DataFrame) -> pd.DataFrame:
    validate_aim_feature_schema(df)
    labeled = df[df["label"].isin(VALID_LABELS)].copy()

    if labeled.empty:
        raise ValueError("No labeled samples available")

    features = prepare_features(labeled)
    labeled = labeled[AIM_FEATURE_COLUMNS].copy()
    labeled[FEATURE_COLUMNS] = features

    return labeled.reset_index(drop=True)