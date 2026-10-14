from pathlib import Path

import pandas as pd

from cs2guard_demo.supervised import evaluate_model, prepare_supervised_data, split_labeled_dataset, train_tuned_models
from cs2guard_demo.supervised.evaluation import print_metrics

INPUT = Path("data/processed/supervised_dataset.csv")
TEST_SIZE = 0.2
RANDOM_STATE = 42


def main() -> None:
    df = pd.read_csv(INPUT)
    train, test = split_labeled_dataset(df, test_size=TEST_SIZE, random_state=RANDOM_STATE)

    X_train, y_train = prepare_supervised_data(train)
    X_test, y_test = prepare_supervised_data(test)

    models = train_tuned_models(X_train, y_train, random_state=RANDOM_STATE)

    print("=== TUNED MODEL EVALUATION ===")
    print(f"Train samples: {len(train)}")
    print(f"Test samples: {len(test)}")
    print(f"Train matches: {train['match_id'].nunique()}")
    print(f"Test matches: {test['match_id'].nunique()}")
    print()

    for name, model in models.items():
        print_metrics(name, evaluate_model(model, X_test, y_test))
        print()


if __name__ == "__main__":
    main()
