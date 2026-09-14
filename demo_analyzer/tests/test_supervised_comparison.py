import numpy as np
import pandas as pd
import pytest

from cs2guard_demo.supervised.comparison import aggregate_player_scores, evaluate_ranked_scores, score_lof_held_out


def test_aggregate_player_scores():
    df = pd.DataFrame(
        {
            "match_id": ["m1", "m1", "m1", "m1"],
            "player_id": ["p1", "p1", "p2", "p2"],
            "label": ["legitimate", "legitimate", "suspicious", "suspicious"],
        }
    )

    result = aggregate_player_scores(df, [0.1, 0.3, 0.7, 0.9], "score")

    assert len(result) == 2
    assert result.loc[result["player_id"] == "p1", "score"].iloc[0] == pytest.approx(0.2)
    assert result.loc[result["player_id"] == "p2", "score"].iloc[0] == pytest.approx(0.8)


def test_evaluate_ranked_scores():
    df = pd.DataFrame(
        {
            "label": ["legitimate", "legitimate", "suspicious", "suspicious"],
            "score": [0.1, 0.2, 0.8, 0.9],
        }
    )

    metrics = evaluate_ranked_scores(df, "score")

    assert metrics["roc_auc"] == pytest.approx(1.0)
    assert metrics["pr_auc"] == pytest.approx(1.0)


def test_score_lof_held_out():
    X_train = pd.DataFrame(
        {
            "x": [0.0, 0.1, -0.1, 0.2, -0.2, 0.05],
            "y": [0.0, 0.1, 0.0, -0.1, 0.1, -0.05],
        }
    )
    X_test = pd.DataFrame(
        {
            "x": [0.0, 5.0],
            "y": [0.0, 5.0],
        }
    )

    scores = score_lof_held_out(X_train, X_test, n_neighbors=2)

    assert len(scores) == 2
    assert np.isfinite(scores).all()
    assert scores[1] > scores[0]