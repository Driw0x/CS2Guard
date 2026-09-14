import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def evaluate_predictions(y_test: pd.Series, predictions, probabilities) -> dict[str, float | int]:
    tn, fp, fn, tp = confusion_matrix(y_test, predictions, labels=[0, 1]).ravel()

    return {
        "precision": precision_score(y_test, predictions, zero_division=0),
        "recall": recall_score(y_test, predictions, zero_division=0),
        "f1": f1_score(y_test, predictions, zero_division=0),
        "roc_auc": roc_auc_score(y_test, probabilities),
        "pr_auc": average_precision_score(y_test, probabilities),
        "false_positive_rate": fp / (fp + tn),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float | int]:
    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = model.predict(X_test)

    return evaluate_predictions(y_test, predictions, probabilities)


def evaluate_threshold(model, X_test: pd.DataFrame, y_test: pd.Series, threshold: float) -> dict[str, float | int]:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")

    probabilities = model.predict_proba(X_test)[:, 1]
    predictions = (probabilities >= threshold).astype(int)

    return evaluate_predictions(y_test, predictions, probabilities)


def analyze_thresholds(
    model,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    thresholds: list[float],
) -> pd.DataFrame:
    rows = []

    for threshold in thresholds:
        metrics = evaluate_threshold(model, X_test, y_test, threshold)
        rows.append(
            {
                "threshold": threshold,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "false_positive_rate": metrics["false_positive_rate"],
                "fp": metrics["fp"],
                "tp": metrics["tp"],
            }
        )

    return pd.DataFrame(rows)