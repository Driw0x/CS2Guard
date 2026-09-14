from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier

from cs2guard_demo.supervised.dataset import prepare_supervised_data
from cs2guard_demo.supervised.models import (
    create_baseline_models,
    create_gradient_boosting_model,
    create_random_forest_model,
    create_tuned_models,
    train_baseline_models,
    train_gradient_boosting_model,
    train_random_forest_model,
    train_tuned_models,
)
from tests.test_supervised_dataset import make_dataset


def test_create_baseline_models():
    models = create_baseline_models()

    assert set(models) == {"dummy", "logistic_regression"}


def test_train_baseline_models():
    dataset = make_dataset()
    dataset = dataset[dataset["label"].notna()].reset_index(drop=True)
    X, y = prepare_supervised_data(dataset)

    models = train_baseline_models(X, y)

    for model in models.values():
        predictions = model.predict(X)
        assert len(predictions) == len(dataset)
        assert set(predictions).issubset({0, 1})


def test_create_random_forest_model():
    model = create_random_forest_model(n_estimators=10)

    assert isinstance(model, RandomForestClassifier)
    assert model.n_estimators == 10
    assert model.max_depth == 20
    assert model.min_samples_leaf == 5


def test_train_random_forest_model():
    dataset = make_dataset()
    dataset = dataset[dataset["label"].notna()].reset_index(drop=True)
    X, y = prepare_supervised_data(dataset)

    model = train_random_forest_model(X, y, n_estimators=10)
    predictions = model.predict(X)

    assert len(predictions) == len(dataset)
    assert set(predictions).issubset({0, 1})


def test_create_gradient_boosting_model():
    model = create_gradient_boosting_model(max_iter=10)

    assert isinstance(model, HistGradientBoostingClassifier)
    assert model.learning_rate == 0.1
    assert model.max_iter == 10
    assert model.max_leaf_nodes == 31


def test_train_gradient_boosting_model():
    dataset = make_dataset()
    dataset = dataset[dataset["label"].notna()].reset_index(drop=True)
    X, y = prepare_supervised_data(dataset)

    model = train_gradient_boosting_model(X, y, max_iter=10)
    predictions = model.predict(X)

    assert len(predictions) == len(dataset)
    assert set(predictions).issubset({0, 1})


def test_create_tuned_models():
    models = create_tuned_models()
    rf = models["random_forest_tuned"]
    hgb = models["hist_gradient_boosting_tuned"]

    assert rf.n_estimators == 150
    assert rf.max_depth == 15
    assert rf.min_samples_leaf == 5
    assert rf.max_features == "sqrt"
    assert hgb.max_leaf_nodes == 63
    assert hgb.max_iter == 150
    assert hgb.learning_rate == 0.1
    assert hgb.l2_regularization == 1.0
    assert hgb.class_weight == "balanced"
    assert hgb.early_stopping is False


def test_train_tuned_models():
    dataset = make_dataset()
    dataset = dataset[dataset["label"].notna()].reset_index(drop=True)
    X, y = prepare_supervised_data(dataset)

    models = train_tuned_models(X, y)

    for model in models.values():
        predictions = model.predict(X)
        assert len(predictions) == len(dataset)
        assert set(predictions).issubset({0, 1})