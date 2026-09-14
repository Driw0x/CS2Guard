from pathlib import Path

import pandas as pd

from cs2guard_demo.supervised.dataset import prepare_supervised_data, split_labeled_dataset
from cs2guard_demo.supervised.tuning import tune_gradient_boosting, tune_random_forest

INPUT = Path("data/processed/supervised_dataset.csv")
TEST_SIZE = 0.2
RANDOM_STATE = 42
N_ITER = 6
CV_SPLITS = 3


def print_result(name: str, search) -> None:
    print()
    print(f"=== {name} ===")
    print(f"Best CV PR-AUC: {search.best_score_:.4f}")
    print("Best parameters:")

    for parameter, value in search.best_params_.items():
        print(f"  {parameter}: {value}")


def main() -> None:
    df = pd.read_csv(INPUT)
    train, test = split_labeled_dataset(df, test_size=TEST_SIZE, random_state=RANDOM_STATE)
    X_train, y_train = prepare_supervised_data(train)
    groups = train["match_id"]

    print("=== HYPERPARAMETER TUNING ===")
    print(f"Train samples: {len(train)}")
    print(f"Train matches: {train['match_id'].nunique()}")
    print(f"Held-out test matches: {test['match_id'].nunique()}")
    print(f"CV folds: {CV_SPLITS}")
    print(f"Configurations per model: {N_ITER}")
    print("Scoring: PR-AUC")

    random_forest = tune_random_forest(
        X_train,
        y_train,
        groups,
        n_iter=N_ITER,
        cv_splits=CV_SPLITS,
        random_state=RANDOM_STATE,
    )
    print_result("RANDOM FOREST", random_forest)

    gradient_boosting = tune_gradient_boosting(
        X_train,
        y_train,
        groups,
        n_iter=N_ITER,
        cv_splits=CV_SPLITS,
        random_state=RANDOM_STATE,
    )
    print_result("HIST GRADIENT BOOSTING", gradient_boosting)


if __name__ == "__main__":
    main()