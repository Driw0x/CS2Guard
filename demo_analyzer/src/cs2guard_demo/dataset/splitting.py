import random

import pandas as pd


VALID_SPLITS = {"train", "validation", "test"}


def _validate_split_ratios(train_ratio: float, validation_ratio: float, test_ratio: float) -> None:
    ratios = [train_ratio, validation_ratio, test_ratio]

    if any(ratio < 0.0 for ratio in ratios):
        raise ValueError("Split ratios cannot be negative.")

    if abs(sum(ratios) - 1.0) > 1e-9:
        raise ValueError("Split ratios must sum to 1.0.")


def build_leakage_groups(dataset: pd.DataFrame) -> pd.Series:
    required_columns = {"match_id", "steamid"}
    missing_columns = required_columns - set(dataset.columns)

    if missing_columns:
        raise ValueError(f"Missing split columns: {sorted(missing_columns)}")

    if dataset.empty:
        return pd.Series(dtype="object", index=dataset.index)

    if dataset["match_id"].isna().any():
        raise ValueError("match_id cannot contain missing values.")

    if dataset["steamid"].isna().any():
        raise ValueError("steamid cannot contain missing values.")

    parent = {}

    def find(node):
        parent.setdefault(node, node)

        if parent[node] != node:
            parent[node] = find(parent[node])

        return parent[node]

    def union(first, second):
        first_root = find(first)
        second_root = find(second)

        if first_root != second_root:
            parent[second_root] = first_root

    for row in dataset[["match_id", "steamid"]].drop_duplicates().itertuples(index=False):
        match_node = f"match:{row.match_id}"
        player_node = f"player:{int(row.steamid)}"
        union(match_node, player_node)

    roots = {}

    for match_id in dataset["match_id"].unique():
        node = f"match:{match_id}"
        root = find(node)
        roots.setdefault(root, f"group_{len(roots)}")

    return dataset["match_id"].map(lambda match_id: roots[find(f"match:{match_id}")])


def create_dataset_splits(
    dataset: pd.DataFrame,
    train_ratio: float = 0.7,
    validation_ratio: float = 0.15,
    test_ratio: float = 0.15,
    random_state: int = 42,
) -> pd.DataFrame:
    _validate_split_ratios(train_ratio, validation_ratio, test_ratio)

    if dataset.empty:
        result = dataset.copy()
        result["split"] = pd.Series(dtype="object")
        return result

    result = dataset.copy()
    result["_leakage_group"] = build_leakage_groups(result)

    group_sizes = result["_leakage_group"].value_counts().to_dict()
    groups = list(group_sizes)

    random.Random(random_state).shuffle(groups)
    groups.sort(key=lambda group: group_sizes[group], reverse=True)

    total_samples = len(result)

    targets = {
        "train": total_samples * train_ratio,
        "validation": total_samples * validation_ratio,
        "test": total_samples * test_ratio,
    }

    current_sizes = {
        "train": 0,
        "validation": 0,
        "test": 0,
    }

    group_assignments = {}

    for group in groups:
        enabled_splits = [split for split, target in targets.items() if target > 0.0]

        selected_split = min(
            enabled_splits,
            key=lambda split: current_sizes[split] / targets[split],
        )

        group_assignments[group] = selected_split
        current_sizes[selected_split] += group_sizes[group]

    result["split"] = result["_leakage_group"].map(group_assignments)
    result = result.drop(columns="_leakage_group")

    return result


def validate_no_data_leakage(dataset: pd.DataFrame) -> None:
    required_columns = {"match_id", "steamid", "split"}
    missing_columns = required_columns - set(dataset.columns)

    if missing_columns:
        raise ValueError(f"Missing leakage validation columns: {sorted(missing_columns)}")

    invalid_splits = set(dataset["split"].dropna()) - VALID_SPLITS

    if invalid_splits:
        raise ValueError(f"Invalid splits: {sorted(invalid_splits)}")

    match_split_counts = dataset.groupby("match_id")["split"].nunique()

    if (match_split_counts > 1).any():
        raise ValueError("Match leakage detected between splits.")

    player_split_counts = dataset.groupby("steamid")["split"].nunique()

    if (player_split_counts > 1).any():
        raise ValueError("Player leakage detected between splits.")