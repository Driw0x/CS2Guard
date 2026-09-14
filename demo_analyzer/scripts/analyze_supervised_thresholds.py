from pathlib import Path

import pandas as pd

from cs2guard_demo.supervised import analyze_thresholds, prepare_supervised_data, split_labeled_dataset, train_tuned_models

INPUT = Path("data/processed/supervised_dataset.csv")
TEST_SIZE = 0.2
RANDOM_STATE = 42
THRESHOLDS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def main() -> None:
    df = pd.read_csv(INPUT)
    train, test = split_labeled_dataset(df, test_size=TEST_SIZE, random_state=RANDOM_STATE)

    X_train, y_train = prepare_supervised_data(train)
    X_test, y_test = prepare_supervised_data(test)

    models = train_tuned_models(X_train, y_train, random_state=RANDOM_STATE)

    print("=== THRESHOLD ANALYSIS ===")
    print(f"Test samples: {len(test)}")
    print(f"Test matches: {test['match_id'].nunique()}")

    for name, model in models.items():
        results = analyze_thresholds(model, X_test, y_test, THRESHOLDS)

        print()
        print(f"=== {name.upper()} ===")
        print(
            results.to_string(
                index=False,
                formatters={
                    "threshold": "{:.2f}".format,
                    "precision": "{:.4f}".format,
                    "recall": "{:.4f}".format,
                    "f1": "{:.4f}".format,
                    "false_positive_rate": "{:.4f}".format,
                },
            )
        )


if __name__ == "__main__":
    main()
