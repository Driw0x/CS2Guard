import numpy as np
import pandas as pd
import pytest

from cs2guard_demo.supervised import create_tuned_models, load_model_bundle, save_model_bundle


def test_save_and_load_model_bundle(tmp_path):
    X = pd.DataFrame(
        {
            "feature_1": [0.0, 0.1, 0.2, 1.0, 1.1, 1.2],
            "feature_2": [0.1, 0.0, 0.2, 1.1, 1.0, 1.2],
        }
    )
    y = pd.Series([0, 0, 0, 1, 1, 1])

    model = create_tuned_models()["random_forest_tuned"]
    model.fit(X, y)
    metadata = {"model_name": "random_forest", "version": "v1"}

    model_path, metadata_path = save_model_bundle(
        model,
        metadata,
        tmp_path,
        "random_forest",
        "v1",
    )
    loaded_model, loaded_metadata = load_model_bundle(model_path, metadata_path)

    assert model_path.exists()
    assert metadata_path.exists()
    assert loaded_metadata == metadata
    assert np.array_equal(model.predict(X), loaded_model.predict(X))


def test_invalid_model_version(tmp_path):
    model = create_tuned_models()["random_forest_tuned"]

    with pytest.raises(ValueError, match="version"):
        save_model_bundle(model, {}, tmp_path, "random_forest", "")
