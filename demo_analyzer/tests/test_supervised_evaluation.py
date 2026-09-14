import numpy as np
import pandas as pd
import pytest

from cs2guard_demo.supervised import analyze_thresholds, evaluate_model, evaluate_threshold


class TestModel:
    def predict(self, X):
        return np.array([0, 1, 0, 1])

    def predict_proba(self, X):
        return np.array(
            [
                [0.9, 0.1],
                [0.2, 0.8],
                [0.8, 0.2],
                [0.1, 0.9],
            ]
        )


class ConstantModel:
    def predict(self, X):
        return np.zeros(len(X), dtype=int)

    def predict_proba(self, X):
        return np.full((len(X), 2), [0.75, 0.25])


def test_evaluate_model():
    X = pd.DataFrame({"feature": [1, 2, 3, 4]})
    y = pd.Series([0, 1, 1, 0])

    metrics = evaluate_model(TestModel(), X, y)

    assert metrics["precision"] == pytest.approx(0.5)
    assert metrics["recall"] == pytest.approx(0.5)
    assert metrics["f1"] == pytest.approx(0.5)
    assert metrics["false_positive_rate"] == pytest.approx(0.5)
    assert metrics["tn"] == 1
    assert metrics["fp"] == 1
    assert metrics["fn"] == 1
    assert metrics["tp"] == 1
    assert 0 <= metrics["roc_auc"] <= 1
    assert 0 <= metrics["pr_auc"] <= 1


def test_constant_model_pr_auc_matches_positive_rate():
    X = pd.DataFrame({"feature": range(10)})
    y = pd.Series([0, 0, 0, 0, 0, 0, 0, 1, 1, 1])

    metrics = evaluate_model(ConstantModel(), X, y)

    assert metrics["roc_auc"] == pytest.approx(0.5)
    assert metrics["pr_auc"] == pytest.approx(0.3)


def test_evaluate_threshold():
    X = pd.DataFrame({"feature": [1, 2, 3, 4]})
    y = pd.Series([0, 1, 1, 0])

    metrics = evaluate_threshold(TestModel(), X, y, threshold=0.85)

    assert metrics["precision"] == pytest.approx(0.0)
    assert metrics["recall"] == pytest.approx(0.0)
    assert metrics["false_positive_rate"] == pytest.approx(0.5)


def test_invalid_threshold():
    X = pd.DataFrame({"feature": [1]})
    y = pd.Series([0])

    with pytest.raises(ValueError, match="threshold"):
        evaluate_threshold(TestModel(), X, y, threshold=1.1)


def test_analyze_thresholds():
    X = pd.DataFrame({"feature": [1, 2, 3, 4]})
    y = pd.Series([0, 1, 1, 0])

    results = analyze_thresholds(TestModel(), X, y, [0.5, 0.8])

    assert len(results) == 2
    assert list(results["threshold"]) == [0.5, 0.8]
    assert set(results.columns) == {
        "threshold",
        "precision",
        "recall",
        "f1",
        "false_positive_rate",
        "fp",
        "tp",
    }
