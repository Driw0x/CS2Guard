from pathlib import Path

import pandas as pd

from cs2guard_demo.supervised.dataset import prepare_supervised_data, split_labeled_dataset
from cs2guard_demo.supervised.models import train_baseline_models

INPUT = Path("data/processed/supervised_dataset.csv")
TEST_SIZE = 0.2
RANDOM_STATE = 42


def main() -> None:
    df = pd.read_csv(INPUT)
    train, test = split_labeled_dataset(df, test_size=TEST_SIZE, random_state=RANDOM_STATE)

    X_train, y_train = prepare_supervised_data(train)
    X_test, y_test = prepare_supervised_data(test)

    models = train_baseline_models(X_train, y_train, random_state=RANDOM_STATE)

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
    print("=== BASELINE CLASSIFIERS ===")

    for name, model in models.items():
        print(f"{name}: accuracy={model.score(X_test, y_test):.4f}")


if __name__ == "__main__":
    main()