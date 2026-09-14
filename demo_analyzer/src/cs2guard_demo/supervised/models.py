import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def create_baseline_models(random_state: int = 42) -> dict:
    return {
        "dummy": DummyClassifier(strategy="prior"),
        "logistic_regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(max_iter=1000, random_state=random_state)),
            ]
        ),
    }


def train_baseline_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42,
) -> dict:
    models = create_baseline_models(random_state)

    for model in models.values():
        model.fit(X_train, y_train)

    return models


def create_random_forest_model(
    random_state: int = 42,
    n_estimators: int = 100,
) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=20,
        min_samples_leaf=5,
        random_state=random_state,
        n_jobs=-1,
    )


def train_random_forest_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42,
    n_estimators: int = 100,
) -> RandomForestClassifier:
    model = create_random_forest_model(random_state, n_estimators)
    model.fit(X_train, y_train)

    return model


def create_gradient_boosting_model(
    random_state: int = 42,
    max_iter: int = 100,
) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        learning_rate=0.1,
        max_iter=max_iter,
        max_leaf_nodes=31,
        random_state=random_state,
    )


def train_gradient_boosting_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42,
    max_iter: int = 100,
) -> HistGradientBoostingClassifier:
    model = create_gradient_boosting_model(random_state, max_iter)
    model.fit(X_train, y_train)

    return model


def create_tuned_models(random_state: int = 42) -> dict:
    return {
        "random_forest_tuned": RandomForestClassifier(
            n_estimators=150,
            max_depth=15,
            min_samples_leaf=5,
            max_features="sqrt",
            class_weight=None,
            random_state=random_state,
            n_jobs=-1,
        ),
        "hist_gradient_boosting_tuned": HistGradientBoostingClassifier(
            max_leaf_nodes=63,
            max_iter=150,
            learning_rate=0.1,
            l2_regularization=1.0,
            class_weight="balanced",
            early_stopping=False,
            random_state=random_state,
        ),
    }


def train_tuned_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    random_state: int = 42,
) -> dict:
    models = create_tuned_models(random_state)

    for model in models.values():
        model.fit(X_train, y_train)

    return models