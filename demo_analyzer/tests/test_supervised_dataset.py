import numpy as np
import pandas as pd
import pytest

from cs2guard_demo.dataset.schema import AIM_FEATURE_COLUMNS
from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS
from cs2guard_demo.supervised.dataset import build_labeled_dataset


def make_dataset() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "source": "cs2cd",
                "match_id": "match_1",
                "player_id": "player_1",
                "source_player_id": "Player_1",
                "identity_scope": "match",
                "label": "legitimate",
                "window_id": "window_1",
                "shot_tick": 100,
                "mean_angular_speed": 10.0,
                "max_angular_speed": 20.0,
                "std_angular_speed": 5.0,
                "mean_angular_acceleration": 100.0,
                "max_angular_acceleration": 200.0,
                "std_angular_acceleration": 50.0,
            },
            {
                "source": "cs2cd",
                "match_id": "match_2",
                "player_id": "player_2",
                "source_player_id": "Player_2",
                "identity_scope": "match",
                "label": "suspicious",
                "window_id": "window_2",
                "shot_tick": 200,
                "mean_angular_speed": 30.0,
                "max_angular_speed": 40.0,
                "std_angular_speed": 10.0,
                "mean_angular_acceleration": 300.0,
                "max_angular_acceleration": 400.0,
                "std_angular_acceleration": 100.0,
            },
            {
                "source": "demo",
                "match_id": "match_3",
                "player_id": "player_3",
                "source_player_id": "123",
                "identity_scope": "global",
                "label": None,
                "window_id": "window_3",
                "shot_tick": 300,
                "mean_angular_speed": 50.0,
                "max_angular_speed": 60.0,
                "std_angular_speed": 15.0,
                "mean_angular_acceleration": 500.0,
                "max_angular_acceleration": 600.0,
                "std_angular_acceleration": 150.0,
            },
        ]
    )


def test_build_labeled_dataset():
    dataset = build_labeled_dataset(make_dataset())

    assert list(dataset.columns) == AIM_FEATURE_COLUMNS
    assert len(dataset) == 2
    assert dataset["label"].tolist() == ["legitimate", "suspicious"]
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