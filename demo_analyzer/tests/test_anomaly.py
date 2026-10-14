import numpy as np
import pandas as pd
import pytest

from cs2guard_demo.detection import (
    FEATURE_COLUMNS,
    compute_suspicion_scores,
    run_isolation_forest,
    run_lof,
    run_one_class_svm,
)
from cs2guard_demo.detection.anomaly import aggregate_player_scores, prepare_features


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


@pytest.mark.parametrize(
    "detector,parameters",
    [
        (run_isolation_forest, {"n_estimators": 20}),
        (run_lof, {"n_neighbors": 2}),
        (run_one_class_svm, {"max_train_samples": 6, "nu": 0.25}),
    ],
)
def test_anomaly_detectors(detector, parameters):
    df = make_dataset()

    windows, players = detector(df, **parameters)

    assert len(windows) == 8
    assert len(players) == 2
    assert windows["anomaly_score"].notna().all()
    assert np.isfinite(windows["anomaly_score"]).all()
    assert windows["is_anomaly"].dtype == bool
    assert players["window_count"].tolist() == [4, 4]
    repeated_windows, repeated_players = detector(df, **parameters)
    pd.testing.assert_frame_equal(windows, repeated_windows)
    pd.testing.assert_frame_equal(players, repeated_players)


def test_run_lof_with_feature_subset():
    df = make_dataset()

    windows, players = run_lof(
        df,
        n_neighbors=2,
        feature_columns=FEATURE_COLUMNS[:-1],
    )

    assert len(windows) == 8
    assert len(players) == 2


@pytest.mark.parametrize(
    "detector,parameters",
    [
        (run_isolation_forest, {"n_estimators": 20}),
        (run_lof, {"n_neighbors": 3}),
        (run_one_class_svm, {"nu": 0.1}),
    ],
)
def test_detector_scores_rank_isolated_window(detector, parameters):
    df = pd.concat([make_dataset().iloc[[0]]] * 21, ignore_index=True)
    for column in FEATURE_COLUMNS:
        df[column] = np.r_[np.linspace(0.0, 1.0, 20), 1000.0]

    windows, _ = detector(df, **parameters)

    assert windows.iloc[-1]["anomaly_score"] > windows.iloc[:-1]["anomaly_score"].max()
    assert windows.iloc[-1]["is_anomaly"]


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


def test_suspicion_scores_use_right_inclusive_legitimate_ecdf():
    df = pd.DataFrame(
        {
            "mean_anomaly_score": [1.0, 1.0, 3.0, 0.0, 4.0],
            "label": ["legitimate", "legitimate", "legitimate", None, "suspicious"],
        }
    )

    scored = compute_suspicion_scores(df)

    assert scored["suspicion_score"].tolist() == pytest.approx([200 / 3, 200 / 3, 100, 0, 100])
    assert "suspicion_score" not in df


@pytest.mark.parametrize(
    "frame,error",
    [
        (pd.DataFrame({"label": ["legitimate"]}), "Missing suspicion score columns"),
        (pd.DataFrame({"label": [None], "mean_anomaly_score": [1.0]}), "No legitimate players"),
        (pd.DataFrame({"label": ["legitimate"], "mean_anomaly_score": [np.inf]}), "NaN or infinite"),
    ],
)
def test_suspicion_score_validation(frame, error):
    with pytest.raises(ValueError, match=error):
        compute_suspicion_scores(frame)


def test_prepare_features_preserves_order_and_numeric_values():
    df = make_dataset()[FEATURE_COLUMNS[::-1]].astype(str)

    features = prepare_features(df)

    assert list(features.columns) == FEATURE_COLUMNS
    pd.testing.assert_frame_equal(features, make_dataset()[FEATURE_COLUMNS])


def test_anomaly_aggregation_preserves_matches_and_unlabeled_players():
    df = make_dataset().iloc[:4].copy()
    df["match_id"] = ["m1", "m1", "m2", "m2"]
    df["label"] = None
    df["anomaly_score"] = [1.0, 3.0, 5.0, 9.0]
    df["is_anomaly"] = [False, True, True, True]

    players = aggregate_player_scores(df)

    assert players["match_id"].tolist() == ["m1", "m2"]
    assert players["label"].isna().all()
    assert players["window_count"].tolist() == [2, 2]
    assert players["mean_anomaly_score"].tolist() == [2.0, 7.0]
    assert players["max_anomaly_score"].tolist() == [3.0, 9.0]
    assert players["anomalous_window_ratio"].tolist() == [0.5, 1.0]


def test_missing_feature():
    df = make_dataset().drop(columns=[FEATURE_COLUMNS[0]])

    with pytest.raises(ValueError, match="Missing feature columns"):
        run_isolation_forest(df)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_invalid_feature_value(value):
    df = make_dataset()
    df.loc[0, FEATURE_COLUMNS[0]] = value

    with pytest.raises(ValueError, match="NaN or infinite"):
        run_isolation_forest(df)
