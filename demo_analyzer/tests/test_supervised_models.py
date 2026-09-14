from cs2guard_demo.supervised.dataset import prepare_supervised_data
from cs2guard_demo.supervised.models import create_baseline_models, train_baseline_models
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