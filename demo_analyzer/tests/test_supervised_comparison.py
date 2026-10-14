import numpy as np
import pandas as pd
import pytest

from cs2guard_demo.supervised import aggregate_player_scores, evaluate_ranked_scores, score_lof_held_out


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


def test_aggregate_scores_are_positional_and_keep_matches_separate():
    df = pd.DataFrame(
        {
            "match_id": ["m1", "m1", "m2"],
            "player_id": ["p1", "p1", "p1"],
            "label": [None, None, None],
        },
        index=[10, 11, 12],
    )

    result = aggregate_player_scores(df, pd.Series([0.1, 0.3, 0.9]), "score")

    assert result["match_id"].tolist() == ["m1", "m2"]
    assert result["label"].isna().all()
    assert result["score"].tolist() == pytest.approx([0.2, 0.9])


@pytest.mark.parametrize("scores,labels,error", [
    ([0.1], ["legitimate", "legitimate"], "Scores must match"),
    ([0.1, 0.9], ["legitimate", "suspicious"], "Inconsistent player labels"),
])
def test_aggregate_player_score_validation(scores, labels, error):
    df = pd.DataFrame({"match_id": ["m1"] * 2, "player_id": ["p1"] * 2, "label": labels})

    with pytest.raises(ValueError, match=error):
        aggregate_player_scores(df, scores, "score")


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


@pytest.mark.parametrize("labels,scores,error", [
    (["unknown", "suspicious"], [0.1, 0.9], "Unknown labels"),
    (["legitimate", "legitimate"], [0.1, 0.9], "Both labels"),
    (["legitimate", "suspicious"], [0.1, np.inf], "NaN or infinite"),
])
def test_ranked_score_validation(labels, scores, error):
    with pytest.raises(ValueError, match=error):
        evaluate_ranked_scores(pd.DataFrame({"label": labels, "score": scores}), "score")


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


@pytest.mark.parametrize("n_neighbors", [0, 2])
def test_held_out_lof_rejects_invalid_neighborhood(n_neighbors):
    X = pd.DataFrame({"x": [0.0, 1.0]})
    with pytest.raises(ValueError, match="n_neighbors"):
        score_lof_held_out(X, X, n_neighbors=n_neighbors)
