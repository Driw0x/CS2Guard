import pandas as pd
from sklearn.dummy import DummyClassifier
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