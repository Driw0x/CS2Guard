from pathlib import Path

import pandas as pd

from cs2guard_demo.supervised import evaluate_model, prepare_supervised_data, split_labeled_dataset, train_baseline_models, train_gradient_boosting_model, train_random_forest_model
from cs2guard_demo.supervised.evaluation import print_metrics

INPUT = Path("data/processed/supervised_dataset.csv")
TEST_SIZE = 0.2
RANDOM_STATE = 42


def main() -> None:
    df = pd.read_csv(INPUT)
    train, test = split_labeled_dataset(df, test_size=TEST_SIZE, random_state=RANDOM_STATE)

    X_train, y_train = prepare_supervised_data(train)
    X_test, y_test = prepare_supervised_data(test)

    models = train_baseline_models(X_train, y_train, random_state=RANDOM_STATE)
    models["random_forest"] = train_random_forest_model(X_train, y_train, random_state=RANDOM_STATE)
    models["hist_gradient_boosting"] = train_gradient_boosting_model(X_train, y_train, random_state=RANDOM_STATE)

    print("=== SUPERVISED SPLIT ===")
    print(f"Train samples: {len(train)}")
    print(f"Test samples: {len(test)}")
    print(f"Train matches: {train['match_id'].nunique()}")
    print(f"Test matches: {test['match_id'].nunique()}")
    print()
    print("=== TRAIN LABELS ===")
    print(train["label"].value_counts().to_string())
    print()
    print("=== TEST LABELS ===")
    print(test["label"].value_counts().to_string())
    print()
    print("=== MODEL EVALUATION ===")

    for name, model in models.items():
        print_metrics(name, evaluate_model(model, X_test, y_test))
        print()


if __name__ == "__main__":
    main()
