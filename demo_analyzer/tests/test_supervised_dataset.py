import numpy as np
import pandas as pd
import pytest

from cs2guard_demo.dataset.schema import AIM_FEATURE_COLUMNS
from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS
from cs2guard_demo.supervised.dataset import build_labeled_dataset, prepare_supervised_data, split_labeled_dataset


def make_dataset() -> pd.DataFrame:
    rows = []

    for i in range(10):
        rows.append(
            {
                "source": "cs2cd",
                "match_id": f"match_{i}",
                "player_id": f"player_{i}",
                "source_player_id": f"Player_{i}",
                "identity_scope": "match",
                "label": "legitimate" if i % 2 == 0 else "suspicious",
                "window_id": f"window_{i}",
                "shot_tick": 100 + i,
                "mean_angular_speed": 10.0 + i,
                "max_angular_speed": 20.0 + i,
                "std_angular_speed": 5.0 + i,
                "mean_angular_acceleration": 100.0 + i,
                "max_angular_acceleration": 200.0 + i,
                "std_angular_acceleration": 50.0 + i,
            }
        )

    rows.append(
        {
            "source": "demo",
            "match_id": "match_unlabeled",
            "player_id": "player_unlabeled",
            "source_player_id": "123",
            "identity_scope": "global",
            "label": None,
            "window_id": "window_unlabeled",
            "shot_tick": 300,
            "mean_angular_speed": 50.0,
            "max_angular_speed": 60.0,
            "std_angular_speed": 15.0,
            "mean_angular_acceleration": 500.0,
            "max_angular_acceleration": 600.0,
            "std_angular_acceleration": 150.0,
        }
    )

    return pd.DataFrame(rows)


def test_build_labeled_dataset():
    dataset = build_labeled_dataset(make_dataset())

    assert list(dataset.columns) == AIM_FEATURE_COLUMNS
    assert len(dataset) == 10
    assert set(dataset["label"]) == {"legitimate", "suspicious"}
    assert dataset[FEATURE_COLUMNS].dtypes.apply(pd.api.types.is_float_dtype).all()


def test_invalid_feature_value():
    df = make_dataset()
    df.loc[0, FEATURE_COLUMNS[0]] = np.nan

    with pytest.raises(ValueError, match="NaN or infinite"):
        build_labeled_dataset(df)


def test_invalid_label():
    df = make_dataset()
    df.loc[0, "label"] = "unknown"

    with pytest.raises(ValueError, match="Invalid labels"):
        build_labeled_dataset(df)


def test_no_labeled_samples():
    df = make_dataset()
    df["label"] = None

    with pytest.raises(ValueError, match="No labeled samples"):
        build_labeled_dataset(df)


def test_split_labeled_dataset():
    train, test = split_labeled_dataset(make_dataset(), test_size=0.2, random_state=42)

    assert set(train["match_id"]).isdisjoint(set(test["match_id"]))
    assert set(train["label"]) == {"legitimate", "suspicious"}
    assert set(test["label"]) == {"legitimate", "suspicious"}
    assert len(train) + len(test) == 10


def test_prepare_supervised_data():
    dataset = build_labeled_dataset(make_dataset())
    X, y = prepare_supervised_data(dataset)

    assert list(X.columns) == FEATURE_COLUMNS
    assert set(y.unique()) == {0, 1}
    assert len(X) == len(y) == 10


def test_invalid_test_size():
    with pytest.raises(ValueError, match="test_size"):
        split_labeled_dataset(make_dataset(), test_size=1.0)