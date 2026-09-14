from pathlib import Path

import pandas as pd

from cs2guard_demo.detection import FEATURE_COLUMNS
from cs2guard_demo.supervised import LABEL_TO_TARGET, aggregate_player_scores, create_tuned_models, evaluate_model, evaluate_ranked_scores, prepare_supervised_data, save_model_bundle, split_labeled_dataset

INPUT = Path("data/processed/supervised_dataset.csv")
OUTPUT_DIR = Path("models/supervised")
MODEL_NAME = "random_forest"
MODEL_VERSION = "v1"
TEST_SIZE = 0.2
RANDOM_STATE = 42


def main() -> None:
    df = pd.read_csv(INPUT)
    train, test = split_labeled_dataset(df, test_size=TEST_SIZE, random_state=RANDOM_STATE)

    X_train, y_train = prepare_supervised_data(train)
    X_test, y_test = prepare_supervised_data(test)

    model = create_tuned_models(random_state=RANDOM_STATE)["random_forest_tuned"]
    model.fit(X_train, y_train)

    event_metrics = evaluate_model(model, X_test, y_test)
    probabilities = model.predict_proba(X_test)[:, 1]
    player_scores = aggregate_player_scores(test, probabilities, "score")
    player_metrics = evaluate_ranked_scores(player_scores, "score")

    metadata = {
        "model_name": MODEL_NAME,
        "version": MODEL_VERSION,
        "features": FEATURE_COLUMNS,
        "label_mapping": LABEL_TO_TARGET,
        "hyperparameters": model.get_params(deep=False),
        "random_state": RANDOM_STATE,
        "decision_threshold": None,
        "training": {
            "samples": len(train),
            "matches": int(train["match_id"].nunique()),
        },
        "test": {
            "samples": len(test),
            "matches": int(test["match_id"].nunique()),
            "player_matches": len(player_scores),
        },
        "metrics": {
            "event": {
                "precision": float(event_metrics["precision"]),
                "recall": float(event_metrics["recall"]),
                "f1": float(event_metrics["f1"]),
                "roc_auc": float(event_metrics["roc_auc"]),
                "pr_auc": float(event_metrics["pr_auc"]),
                "false_positive_rate": float(event_metrics["false_positive_rate"]),
                "tn": int(event_metrics["tn"]),
                "fp": int(event_metrics["fp"]),
                "fn": int(event_metrics["fn"]),
                "tp": int(event_metrics["tp"]),
            },
            "player": {
                "roc_auc": float(player_metrics["roc_auc"]),
                "pr_auc": float(player_metrics["pr_auc"]),
            },
        },
    }

    model_path, metadata_path = save_model_bundle(
        model,
        metadata,
        OUTPUT_DIR,
        MODEL_NAME,
        MODEL_VERSION,
    )

    print("=== MODEL PERSISTENCE ===")
    print(f"Model: {MODEL_NAME}")
    print(f"Version: {MODEL_VERSION}")
    print(f"Train matches: {metadata['training']['matches']}")
    print(f"Test matches: {metadata['test']['matches']}")
    print(f"Player ROC-AUC: {metadata['metrics']['player']['roc_auc']:.4f}")
    print(f"Player PR-AUC: {metadata['metrics']['player']['pr_auc']:.4f}")
    print(f"Model saved to: {model_path}")
    print(f"Metadata saved to: {metadata_path}")


if __name__ == "__main__":
    main()
