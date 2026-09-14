import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

from cs2guard_demo.dataset.schema import AIM_FEATURE_COLUMNS, VALID_LABELS, validate_aim_feature_schema
from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS, prepare_features

LABEL_TO_TARGET = {
    "legitimate": 0,
    "suspicious": 1,
}


def build_labeled_dataset(df: pd.DataFrame) -> pd.DataFrame:
    validate_aim_feature_schema(df)
    labeled = df[df["label"].isin(VALID_LABELS)].copy()

    if labeled.empty:
        raise ValueError("No labeled samples available")

    features = prepare_features(labeled)
    labeled = labeled[AIM_FEATURE_COLUMNS].copy()
    labeled[FEATURE_COLUMNS] = features

    return labeled.reset_index(drop=True)


def split_labeled_dataset(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")

    dataset = build_labeled_dataset(df)
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(splitter.split(dataset, groups=dataset["match_id"]))

    train = dataset.iloc[train_idx].reset_index(drop=True)
    test = dataset.iloc[test_idx].reset_index(drop=True)

    if set(train["match_id"]) & set(test["match_id"]):
        raise RuntimeError("Train and test sets contain overlapping matches")

    if set(train["label"]) != VALID_LABELS or set(test["label"]) != VALID_LABELS:
        raise ValueError("Train and test sets must both contain all labels")

    return train, test


def prepare_supervised_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    features = prepare_features(df)
    labels = df["label"].map(LABEL_TO_TARGET)

    if labels.isna().any():
        raise ValueError("Unknown labels in supervised dataset")

    return features, labels.astype(int)