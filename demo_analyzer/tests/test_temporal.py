import json

import numpy as np
import pandas as pd
import pytest

from cs2guard_demo.dataset.schema import AIM_FEATURE_COLUMNS
from cs2guard_demo.temporal import (
    TEMPORAL_CHANNELS, WINDOW_SIZE, benchmark_summary, build_inference_sequences,
    build_sequence_arrays, build_sequence_arrays_from_csv, create_match_splits, load_temporal_dataset,
    normalize_sequences, paired_match_bootstrap_difference, save_temporal_dataset, sequence_channels,
    temporal_metrics, train_temporal_baselines,
)


def make_window(window_id="w1", match_id="m1", player_id="p1", *, yaw_start=170.0):
    rows = []
    for offset in range(WINDOW_SIZE):
        rows.append({
            "window_id": window_id, "window_offset": offset, "tick": 100 + offset,
            "yaw": ((yaw_start + offset * 2 + 180) % 360) - 180,
            "pitch": float(offset), "match_id": match_id, "player_id": player_id,
        })
    return pd.DataFrame(rows)


def make_features(matches=10):
    rows = []
    for match in range(matches):
        for target, label in enumerate(("legitimate", "suspicious")):
            rows.append({
                "source": "test", "match_id": f"m{match}", "player_id": f"p{match}_{target}",
                "source_player_id": f"s{match}_{target}", "identity_scope": "match", "label": label,
                "window_id": f"w{match}_{target}", "shot_tick": 131,
                "mean_angular_speed": 1.0 + target, "max_angular_speed": 2.0 + target,
                "std_angular_speed": 0.5, "mean_angular_acceleration": 1.0,
                "max_angular_acceleration": 2.0, "std_angular_acceleration": 0.5,
            })
    return pd.DataFrame(rows, columns=AIM_FEATURE_COLUMNS)


def test_sequence_channels_handle_yaw_wrap():
    sequence = sequence_channels(make_window())
    assert sequence.shape == (32, 6)
    assert sequence[1, 0] == pytest.approx(128.0)
    assert np.isfinite(sequence).all()


def test_sequence_channels_reject_incomplete_window():
    with pytest.raises(ValueError, match="exactly 32"):
        sequence_channels(make_window().iloc[:-1])


def test_match_splits_are_disjoint_and_keep_m5_test():
    features = make_features(20)
    splits = create_match_splits(features)
    assert not splits["train"] & splits["validation"]
    assert not splits["train"] & splits["test"]
    assert not splits["validation"] & splits["test"]
    assert set.union(*splits.values()) == set(features["match_id"])


def test_dataset_round_trip_and_train_only_normalization(tmp_path):
    features = make_features(6)
    windows = pd.concat([
        make_window(row.window_id, row.match_id, row.player_id)
        for row in features.itertuples(index=False)
    ], ignore_index=True)
    splits = {"train": {"m0", "m1"}, "validation": {"m2", "m3"}, "test": {"m4", "m5"}}
    arrays = build_sequence_arrays(windows, features, splits=splits)
    path, metadata_path = save_temporal_dataset(arrays, tmp_path / "temporal.npz")
    loaded, metadata = load_temporal_dataset(path)
    assert loaded["X"].shape == (12, 32, 6)
    assert loaded["X"][loaded["split"] == "train"].mean(axis=(0, 1)) == pytest.approx(np.zeros(6), abs=1e-5)
    assert metadata["channels"] == TEMPORAL_CHANNELS
    assert json.loads(metadata_path.read_text())["normalization"]["fit_split"] == "train"


def test_inference_sequences_keep_feature_order():
    features = make_features(1).iloc[::-1].reset_index(drop=True)
    windows = pd.concat([make_window(row.window_id, row.match_id, row.player_id) for row in features.itertuples()], ignore_index=True)
    sequences, aligned = build_inference_sequences(windows, features)
    assert sequences.shape == (2, 32, 6)
    assert aligned["window_id"].tolist() == features["window_id"].tolist()


def test_streaming_csv_keeps_windows_split_across_chunks(tmp_path):
    features = make_features(3)
    windows = pd.concat([make_window(row.window_id, row.match_id, row.player_id) for row in features.itertuples()], ignore_index=True)
    path = tmp_path / "windows.csv"
    windows.to_csv(path, index=False)
    splits = {"train": {"m0"}, "validation": {"m1"}, "test": {"m2"}}
    arrays = build_sequence_arrays_from_csv(path, features, splits=splits, chunk_size=17)
    assert arrays["X"].shape == (6, 32, 6)
    assert arrays["split"].tolist() == ["train", "train", "validation", "validation", "test", "test"]
    dataset, _ = save_temporal_dataset(arrays, tmp_path / "streamed.npz")
    loaded, _ = load_temporal_dataset(dataset)
    assert loaded["window_id"].tolist() == arrays["window_id"].tolist()


def test_baseline_and_metrics():
    rng = np.random.default_rng(42)
    arrays = {
        "X": rng.normal(size=(12, 32, 6)).astype(np.float32),
        "y": np.tile([0, 1], 6),
        "split": np.repeat(["train", "validation", "test"], 4),
        "match_id": np.array([f"m{i // 2}" for i in range(12)]),
        "player_id": np.array([f"p{i}" for i in range(12)]),
        "window_id": np.array([f"w{i}" for i in range(12)]),
    }
    models = train_temporal_baselines(arrays)
    selected = arrays["split"] == "validation"
    probabilities = models["logistic_regression"].predict_proba(arrays["X"][selected].reshape(4, -1))[:, 1]
    metrics = temporal_metrics(arrays, probabilities, "validation")
    assert set(metrics) == {"window", "player"}
    assert 0 <= metrics["player"]["pr_auc"] <= 1


def test_normalization_and_benchmark_validation():
    with pytest.raises(ValueError):
        normalize_sequences(np.array([np.nan]), [0], [1])
    assert benchmark_summary([0.1, 0.2])["median_seconds"] == pytest.approx(0.15)
    bootstrap = paired_match_bootstrap_difference(
        ["a", "a", "b", "b"], [0, 1, 0, 1], [0.1, 0.9, 0.2, 0.8], [0.4, 0.6, 0.3, 0.7],
        metric="pr_auc", iterations=20,
    )
    assert bootstrap["resampling_unit"] == "match"


def test_torch_models_train_persist_and_explain(tmp_path):
    pytest.importorskip("torch")
    from cs2guard_demo.temporal_models import (
        benchmark_model, create_temporal_model, load_temporal_bundle, occlusion_importance,
        predict_probabilities, save_temporal_bundle, train_temporal_model,
    )

    rng = np.random.default_rng(42)
    arrays = {
        "X": rng.normal(size=(24, 32, 6)).astype(np.float32),
        "y": np.tile([0, 1], 12),
        "split": np.repeat(["train", "validation", "test"], 8),
        "match_id": np.array([f"m{i // 2}" for i in range(24)]),
        "player_id": np.array([f"p{i}" for i in range(24)]),
        "window_id": np.array([f"w{i}" for i in range(24)]),
    }
    model = None
    for family in ("cnn1d", "lstm", "gru", "transformer"):
        assert create_temporal_model(family)(pytest.importorskip("torch").zeros(2, 32, 6)).shape == (2,)
        trained, history = train_temporal_model(family, arrays, epochs=1, batch_size=4, device="cpu")
        assert len(history) == 1
        if family == "cnn1d":
            model = trained
    metadata = {
        "model_family": "temporal", "model_name": "cnn1d", "version": "test", "architecture": "cnn1d",
        "hidden_size": 32, "channels": TEMPORAL_CHANNELS, "window_size": 32, "tick_rate": 64.0,
        "normalization": {"mean": [0] * 6, "scale": [1] * 6},
        "label_mapping": {"legitimate": 0, "suspicious": 1},
    }
    path, _ = save_temporal_bundle(model, metadata, tmp_path / "cnn.pt")
    loaded, loaded_metadata = load_temporal_bundle(path)
    probabilities = predict_probabilities(loaded, arrays["X"][:2], device="cpu")
    importance = occlusion_importance(loaded, arrays["X"][:1])
    benchmark = benchmark_model(loaded, arrays["X"][:1], repeats=2, warmups=1, device="cpu")
    assert loaded_metadata["architecture"] == "cnn1d"
    assert probabilities.shape == (2,)
    assert importance["by_step"].shape == (1, 32)
    assert importance["by_channel"].shape == (1, 6)
    assert benchmark["device"] == "cpu"
