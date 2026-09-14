import numpy as np
import pandas as pd
import pytest

from cs2guard_demo.detection.anomaly import (
    FEATURE_COLUMNS,
    compute_suspicion_scores,
    run_isolation_forest,
    run_lof,
    run_one_class_svm,
)


def make_dataset() -> pd.DataFrame:
    rows = []

    for player_id, offset in [("Player_1", 0.0), ("Player_2", 100.0)]:
        for index in range(4):
            rows.append(
                {
                    "window_id": f"{player_id}_{index}",
                    "match_id": "match_1",
                    "weapon": "ak47",
                    "shot_tick": index,
                    "mean_angular_speed": 10.0 + offset + index,
                    "max_angular_speed": 20.0 + offset + index,
                    "std_angular_speed": 5.0 + offset + index,
                    "mean_angular_acceleration": 100.0 + offset + index,
                    "max_angular_acceleration": 200.0 + offset + index,
                    "std_angular_acceleration": 50.0 + offset + index,
                    "source": "cs2cd",
                    "player_id": player_id,
                    "source_player_id": player_id,
                    "identity_scope": "match",
                    "label": "legitimate" if player_id == "Player_1" else "suspicious",
                }
            )

    return pd.DataFrame(rows)


def test_run_isolation_forest():
    df = make_dataset()

    windows, players = run_isolation_forest(df, n_estimators=20)

    assert len(windows) == 8
    assert len(players) == 2
    assert windows["anomaly_score"].notna().all()
    assert np.isfinite(windows["anomaly_score"]).all()
    assert windows["is_anomaly"].dtype == bool
    assert players["window_count"].tolist() == [4, 4]


def test_run_lof():
    df = make_dataset()

    windows, players = run_lof(df, n_neighbors=2)

    assert len(windows) == 8
    assert len(players) == 2
    assert windows["anomaly_score"].notna().all()
    assert np.isfinite(windows["anomaly_score"]).all()
    assert windows["is_anomaly"].dtype == bool
    assert players["window_count"].tolist() == [4, 4]


def test_run_lof_with_feature_subset():
    df = make_dataset()

    windows, players = run_lof(
        df,
        n_neighbors=2,
        feature_columns=FEATURE_COLUMNS[:-1],
    )

    assert len(windows) == 8
    assert len(players) == 2


def test_run_one_class_svm():
    df = make_dataset()

    windows, players = run_one_class_svm(
        df,
        max_train_samples=6,
        nu=0.25,
    )

    assert len(windows) == 8
    assert len(players) == 2
    assert windows["anomaly_score"].notna().all()
    assert np.isfinite(windows["anomaly_score"]).all()
    assert windows["is_anomaly"].dtype == bool
    assert players["window_count"].tolist() == [4, 4]


def test_compute_suspicion_scores():
    df = pd.DataFrame(
        {
            "mean_anomaly_score": [1.0, 2.0, 3.0, 4.0],
            "label": ["legitimate", "legitimate", "suspicious", None],
        }
    )

    scored = compute_suspicion_scores(df)

    assert scored["suspicion_score"].between(0, 100).all()
    assert scored.loc[2, "suspicion_score"] == 100.0
    assert scored.loc[3, "suspicion_score"] == 100.0


def test_missing_feature():
    df = make_dataset().drop(columns=[FEATURE_COLUMNS[0]])

    with pytest.raises(ValueError, match="Missing feature columns"):
        run_isolation_forest(df)


def test_invalid_feature_value():
    df = make_dataset()
    df.loc[0, FEATURE_COLUMNS[0]] = np.nan

    with pytest.raises(ValueError, match="NaN or infinite"):
        run_isolation_forest(df)