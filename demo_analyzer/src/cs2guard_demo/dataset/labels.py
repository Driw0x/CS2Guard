import pandas as pd


VALID_LABELS = {"legitimate", "suspicious"}


def validate_labels(labels: pd.DataFrame) -> None:
    required_columns = {"match_id", "steamid", "label"}
    missing_columns = required_columns - set(labels.columns)

    if missing_columns:
        raise ValueError(f"Missing label columns: {sorted(missing_columns)}")

    invalid_labels = set(labels["label"].dropna()) - VALID_LABELS

    if invalid_labels:
        raise ValueError(f"Invalid labels: {sorted(invalid_labels)}")

    player_labels = labels[labels["steamid"].notna()]

    if player_labels.duplicated(["match_id", "steamid"]).any():
        raise ValueError("Duplicate player labels detected.")

    match_labels = labels[labels["steamid"].isna()]

    if match_labels.duplicated(["match_id"]).any():
        raise ValueError("Duplicate match labels detected.")


def apply_labels(dataset: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    if dataset.empty:
        return dataset.copy()

    validate_labels(labels)

    labeled = dataset.copy()
    labeled["label"] = pd.NA

    match_labels = labels[labels["steamid"].isna()].set_index("match_id")["label"]

    labeled["label"] = labeled["match_id"].map(match_labels)

    player_labels = labels[labels["steamid"].notna()].copy()
    player_labels["steamid"] = player_labels["steamid"].astype(int)
    player_labels = player_labels.set_index(["match_id", "steamid"])["label"]

    keys = pd.MultiIndex.from_arrays([labeled["match_id"], labeled["steamid"]])
    player_values = player_labels.reindex(keys)

    override_mask = player_values.notna().to_numpy()
    labeled.loc[override_mask, "label"] = player_values[override_mask].to_numpy()

    return labeled