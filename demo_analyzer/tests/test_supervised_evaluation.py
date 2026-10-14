import numpy as np
import pandas as pd
import pytest

from cs2guard_demo.supervised import analyze_thresholds, evaluate_model, evaluate_predictions, evaluate_threshold
from cs2guard_demo.supervised.evaluation import print_metrics


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


def test_threshold_includes_equal_probability():
    X = pd.DataFrame({"feature": [1, 2, 3, 4]})
    y = pd.Series([0, 1, 1, 0])

    metrics = evaluate_threshold(TestModel(), X, y, threshold=0.8)

    assert metrics["tp"] == 1
    assert metrics["fp"] == 1
    assert metrics["tn"] == 1
    assert metrics["fn"] == 1


@pytest.mark.parametrize("labels", [[], [0, 0], [1, 1], [0, 2]])
def test_evaluation_rejects_undefined_binary_metrics(labels):
    with pytest.raises(ValueError, match="Both target classes"):
        evaluate_predictions(pd.Series(labels), labels, [0.5] * len(labels))


def test_metric_printing_preserves_script_output(capsys):
    metrics = evaluate_predictions(pd.Series([0, 1]), [0, 1], [0.1, 0.9])

    print_metrics("random_forest", metrics)

    assert capsys.readouterr().out == (
        "random_forest\n"
        "  Precision: 1.0000\n"
        "  Recall:    1.0000\n"
        "  F1-score:  1.0000\n"
        "  ROC-AUC:   1.0000\n"
        "  PR-AUC:    1.0000\n"
        "  FPR:       0.0000\n"
        "  TN=1 FP=0 FN=0 TP=1\n"
    )


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
