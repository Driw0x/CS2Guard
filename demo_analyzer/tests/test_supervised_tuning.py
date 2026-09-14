from cs2guard_demo.supervised import build_labeled_dataset, create_group_cv, prepare_supervised_data, tune_gradient_boosting, tune_random_forest
from tests.test_supervised_dataset import make_dataset


def prepare_test_data():
    dataset = build_labeled_dataset(make_dataset())
    X, y = prepare_supervised_data(dataset)

    return dataset, X, y


def test_group_cv():
    dataset, X, y = prepare_test_data()
    groups = dataset["match_id"]
    cv = create_group_cv(n_splits=2)

    for train_idx, test_idx in cv.split(X, y, groups):
        train_groups = set(groups.iloc[train_idx])
        test_groups = set(groups.iloc[test_idx])

        assert train_groups.isdisjoint(test_groups)


def test_tune_random_forest():
    dataset, X, y = prepare_test_data()
    search = tune_random_forest(X, y, dataset["match_id"], n_iter=1, cv_splits=2)

    assert 0 <= search.best_score_ <= 1
    assert search.best_params_
    assert search.best_estimator_ is not None


def test_tune_gradient_boosting():
    dataset, X, y = prepare_test_data()
    search = tune_gradient_boosting(X, y, dataset["match_id"], n_iter=1, cv_splits=2)

    assert 0 <= search.best_score_ <= 1
    assert search.best_params_
    assert search.best_estimator_ is not None
