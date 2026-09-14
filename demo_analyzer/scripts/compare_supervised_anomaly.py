from pathlib import Path

import pandas as pd

from cs2guard_demo.supervised.comparison import aggregate_player_scores, evaluate_ranked_scores, score_lof_held_out
from cs2guard_demo.supervised.dataset import prepare_supervised_data, split_labeled_dataset
from cs2guard_demo.supervised.models import train_tuned_models

INPUT = Path("data/processed/supervised_dataset.csv")
TEST_SIZE = 0.2
RANDOM_STATE = 42


def main() -> None:
    df = pd.read_csv(INPUT)
    train, test = split_labeled_dataset(df, test_size=TEST_SIZE, random_state=RANDOM_STATE)

    X_train, y_train = prepare_supervised_data(train)
    X_test, _ = prepare_supervised_data(test)

    models = train_tuned_models(X_train, y_train, random_state=RANDOM_STATE)
    results = []

    for name, model in models.items():
        probabilities = model.predict_proba(X_test)[:, 1]
        player_scores = aggregate_player_scores(test, probabilities, "score")
        metrics = evaluate_ranked_scores(player_scores, "score")
        results.append(
            {
                "model": name,
                "player_matches": len(player_scores),
                **metrics,
            }
        )

    lof_scores = score_lof_held_out(X_train, X_test)
    player_scores = aggregate_player_scores(test, lof_scores, "score")
    metrics = evaluate_ranked_scores(player_scores, "score")
    results.append(
        {
            "model": "lof_held_out",
            "player_matches": len(player_scores),
            **metrics,
        }
    )

    results_df = pd.DataFrame(results).sort_values("pr_auc", ascending=False)

    print("=== SUPERVISED VS ANOMALY DETECTION ===")
    print(f"Train matches: {train['match_id'].nunique()}")
    print(f"Test matches: {test['match_id'].nunique()}")
    print()
    print(
        results_df.to_string(
            index=False,
            formatters={
                "roc_auc": "{:.4f}".format,
                "pr_auc": "{:.4f}".format,
            },
        )
    )


if __name__ == "__main__":
    main()