import pandas as pd
from sklearn.model_selection import RandomizedSearchCV, StratifiedGroupKFold

from cs2guard_demo.supervised.models import create_gradient_boosting_model, create_random_forest_model

RF_PARAMETERS = {
    "n_estimators": [100, 150, 200],
    "max_depth": [15, 20, 30],
    "min_samples_leaf": [1, 5, 10],
    "max_features": ["sqrt", None],
    "class_weight": [None, "balanced"],
}

HGB_PARAMETERS = {
    "learning_rate": [0.03, 0.05, 0.1],
    "max_iter": [100, 150, 200],
    "max_leaf_nodes": [15, 31, 63],
    "l2_regularization": [0.0, 0.1, 1.0],
    "class_weight": [None, "balanced"],
}


def create_group_cv(n_splits: int = 3, random_state: int = 42) -> StratifiedGroupKFold:
    if n_splits < 2:
        raise ValueError("n_splits must be at least 2")

    return StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)


def tune_random_forest(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    groups: pd.Series,
    n_iter: int = 6,
    cv_splits: int = 3,
    random_state: int = 42,
) -> RandomizedSearchCV:
    search = RandomizedSearchCV(
        estimator=create_random_forest_model(random_state=random_state),
        param_distributions=RF_PARAMETERS,
        n_iter=n_iter,
        scoring="average_precision",
        cv=create_group_cv(cv_splits, random_state),
        refit=True,
        random_state=random_state,
        n_jobs=1,
        verbose=1,
    )
    search.fit(X_train, y_train, groups=groups)

    return search


def tune_gradient_boosting(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    groups: pd.Series,
    n_iter: int = 6,
    cv_splits: int = 3,
    random_state: int = 42,
) -> RandomizedSearchCV:
    model = create_gradient_boosting_model(random_state=random_state)
    model.set_params(early_stopping=False)

    search = RandomizedSearchCV(
        estimator=model,
        param_distributions=HGB_PARAMETERS,
        n_iter=n_iter,
        scoring="average_precision",
        cv=create_group_cv(cv_splits, random_state),
        refit=True,
        random_state=random_state,
        n_jobs=1,
        verbose=1,
    )
    search.fit(X_train, y_train, groups=groups)

    return search