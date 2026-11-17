"""Temporal sequence dataset and evaluation utilities for M7."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from cs2guard_demo.supervised import LABEL_TO_TARGET, aggregate_player_scores, evaluate_predictions, split_labeled_dataset


WINDOW_SIZE = 32
TICK_RATE = 64.0
RANDOM_STATE = 42
TEMPORAL_CHANNELS = [
    "yaw_velocity",
    "pitch_velocity",
    "angular_speed",
    "yaw_acceleration",
    "pitch_acceleration",
    "angular_acceleration",
]


def _angular_delta(values: np.ndarray) -> np.ndarray:
    return (np.diff(values) + 180.0) % 360.0 - 180.0


def sequence_channels(window: pd.DataFrame, tick_rate: float = TICK_RATE) -> np.ndarray:
    """Convert one canonical tick window to six aim-kinematic channels."""
    if tick_rate <= 0:
        raise ValueError("tick_rate must be greater than zero")
    required = {"tick", "yaw", "pitch"}
    missing = required - set(window.columns)
    if missing:
        raise ValueError(f"Missing temporal columns: {sorted(missing)}")

    order = "window_offset" if "window_offset" in window else "tick"
    ordered = window.sort_values(order)
    if len(ordered) != WINDOW_SIZE:
        raise ValueError(f"Temporal windows must contain exactly {WINDOW_SIZE} ticks")
    ticks = ordered["tick"].to_numpy(dtype=float)
    tick_delta = np.diff(ticks)
    if not np.isfinite(ticks).all() or (tick_delta <= 0).any():
        raise ValueError("Temporal ticks must be finite and strictly increasing")
    dt = tick_delta / tick_rate
    yaw = ordered["yaw"].to_numpy(dtype=float)
    pitch = ordered["pitch"].to_numpy(dtype=float)
    if not np.isfinite(yaw).all() or not np.isfinite(pitch).all():
        raise ValueError("Temporal angles must be finite")

    yaw_velocity = np.zeros(WINDOW_SIZE, dtype=np.float32)
    pitch_velocity = np.zeros(WINDOW_SIZE, dtype=np.float32)
    yaw_velocity[1:] = _angular_delta(yaw) / dt
    pitch_velocity[1:] = np.diff(pitch) / dt
    angular_speed = np.hypot(yaw_velocity, pitch_velocity)
    yaw_acceleration = np.zeros(WINDOW_SIZE, dtype=np.float32)
    pitch_acceleration = np.zeros(WINDOW_SIZE, dtype=np.float32)
    yaw_acceleration[2:] = np.diff(yaw_velocity[1:]) / dt[1:]
    pitch_acceleration[2:] = np.diff(pitch_velocity[1:]) / dt[1:]
    angular_acceleration = np.hypot(yaw_acceleration, pitch_acceleration)
    sequence = np.column_stack((
        yaw_velocity, pitch_velocity, angular_speed,
        yaw_acceleration, pitch_acceleration, angular_acceleration,
    )).astype(np.float32)
    if not np.isfinite(sequence).all():
        raise ValueError("Temporal sequence contains non-finite values")
    return sequence


def create_match_splits(
    features: pd.DataFrame,
    *,
    test_size: float = 0.2,
    validation_size: float = 0.2,
    random_state: int = RANDOM_STATE,
) -> dict[str, set[str]]:
    """Reuse the M5 held-out split and take validation matches from its train side."""
    train_validation, test = split_labeled_dataset(features, test_size=test_size, random_state=random_state)
    splitter = GroupShuffleSplit(n_splits=1, test_size=validation_size, random_state=random_state)
    train_index, validation_index = next(splitter.split(train_validation, groups=train_validation["match_id"]))
    train = train_validation.iloc[train_index]
    validation = train_validation.iloc[validation_index]
    splits = {
        "train": set(train["match_id"].astype(str)),
        "validation": set(validation["match_id"].astype(str)),
        "test": set(test["match_id"].astype(str)),
    }
    if any(splits[left] & splits[right] for left, right in (("train", "validation"), ("train", "test"), ("validation", "test"))):
        raise RuntimeError("Temporal match splits overlap")
    for name, matches in splits.items():
        labels = set(features.loc[features["match_id"].astype(str).isin(matches), "label"].dropna())
        if labels != set(LABEL_TO_TARGET):
            raise ValueError(f"Temporal {name} split must contain both labels")
    return splits


def build_sequence_arrays(
    windows: pd.DataFrame,
    features: pd.DataFrame,
    *,
    splits: dict[str, set[str]] | None = None,
) -> dict[str, np.ndarray]:
    """Build aligned sequence arrays from canonical windows and M5 feature rows."""
    required = {"window_id", "match_id", "player_id", "label"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"Missing temporal feature columns: {sorted(missing)}")
    if features["window_id"].duplicated().any():
        raise ValueError("Temporal feature window_id values must be unique")
    splits = splits or create_match_splits(features)
    split_by_match = {match: name for name, matches in splits.items() for match in matches}
    groups = {str(key): value for key, value in windows.groupby("window_id", sort=False)}
    rows = features[features["label"].isin(LABEL_TO_TARGET)].copy()
    sequences, kept = [], []
    for row in rows.to_dict("records"):
        window = groups.get(str(row["window_id"]))
        split = split_by_match.get(str(row["match_id"]))
        if window is None or split is None:
            continue
        try:
            sequence = sequence_channels(window)
        except ValueError:
            continue
        sequences.append(sequence)
        kept.append((str(row["window_id"]), str(row["match_id"]), str(row["player_id"]), LABEL_TO_TARGET[row["label"]], split))
    if not sequences:
        raise ValueError("No complete labeled temporal sequences available")
    identifiers = np.asarray(kept, dtype=object)
    return {
        "X": np.stack(sequences).astype(np.float32),
        "window_id": identifiers[:, 0].astype(str),
        "match_id": identifiers[:, 1].astype(str),
        "player_id": identifiers[:, 2].astype(str),
        "y": identifiers[:, 3].astype(np.int64),
        "split": identifiers[:, 4].astype(str),
    }


def build_sequence_arrays_from_csv(
    path: str | Path,
    features: pd.DataFrame,
    *,
    splits: dict[str, set[str]],
    chunk_size: int = 500_000,
) -> dict[str, np.ndarray]:
    """Stream the multi-gigabyte canonical window CSV without retaining tick rows."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    rows = features[features["label"].isin(LABEL_TO_TARGET)].reset_index(drop=True)
    if rows["window_id"].duplicated().any():
        raise ValueError("Temporal feature window_id values must be unique")
    split_by_match = {match: name for name, matches in splits.items() for match in matches}
    index_by_window = {str(window_id): index for index, window_id in enumerate(rows["window_id"])}
    sequences = np.empty((len(rows), WINDOW_SIZE, len(TEMPORAL_CHANNELS)), dtype=np.float32)
    valid = np.zeros(len(rows), dtype=bool)
    carry = pd.DataFrame()

    def consume(frame: pd.DataFrame) -> None:
        for window_id, window in frame.groupby("window_id", sort=False):
            index = index_by_window.get(str(window_id))
            if index is None:
                continue
            try:
                sequences[index] = sequence_channels(window)
            except ValueError:
                continue
            valid[index] = True

    reader = pd.read_csv(path, usecols=["window_id", "window_offset", "tick", "yaw", "pitch"], chunksize=chunk_size)
    for chunk in reader:
        chunk = chunk[chunk["window_id"].astype(str).isin(index_by_window)]
        if chunk.empty and carry.empty:
            continue
        combined = pd.concat((carry, chunk), ignore_index=True) if not carry.empty else chunk
        last_id = combined.iloc[-1]["window_id"]
        last = combined["window_id"] == last_id
        consume(combined[~last])
        carry = combined[last].copy()
    if not carry.empty:
        consume(carry)
    if not valid.any():
        raise ValueError("No complete labeled temporal sequences available")
    kept = rows[valid]
    split = kept["match_id"].astype(str).map(split_by_match)
    if split.isna().any():
        raise ValueError("Temporal feature rows contain matches outside the frozen splits")
    return {
        "X": sequences[valid],
        "window_id": kept["window_id"].astype(str).to_numpy(dtype=str),
        "match_id": kept["match_id"].astype(str).to_numpy(dtype=str),
        "player_id": kept["player_id"].astype(str).to_numpy(dtype=str),
        "y": kept["label"].map(LABEL_TO_TARGET).to_numpy(dtype=np.int64),
        "split": split.astype(str).to_numpy(dtype=str),
    }


def build_inference_sequences(windows: pd.DataFrame, features: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    """Build sequences in feature-row order without requiring labels or dataset splits."""
    if "window_id" not in features:
        raise ValueError("Inference features require window_id")
    groups = {str(key): value for key, value in windows.groupby("window_id", sort=False)}
    sequences, indices = [], []
    for index, window_id in enumerate(features["window_id"].astype(str)):
        window = groups.get(window_id)
        if window is None:
            continue
        try:
            sequences.append(sequence_channels(window))
        except ValueError:
            continue
        indices.append(index)
    if not sequences:
        return np.empty((0, WINDOW_SIZE, len(TEMPORAL_CHANNELS)), dtype=np.float32), features.iloc[0:0].copy()
    return np.stack(sequences).astype(np.float32), features.iloc[indices].reset_index(drop=True)


def fit_normalization(sequences: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if sequences.ndim != 3 or sequences.shape[1:] != (WINDOW_SIZE, len(TEMPORAL_CHANNELS)):
        raise ValueError("Temporal sequences must have shape [N, 32, 6]")
    mean = sequences.mean(axis=(0, 1), dtype=np.float64).astype(np.float32)
    scale = sequences.std(axis=(0, 1), dtype=np.float64).astype(np.float32)
    scale[scale == 0] = 1.0
    return mean, scale


def normalize_sequences(sequences: np.ndarray, mean, scale) -> np.ndarray:
    normalized = (np.asarray(sequences, dtype=np.float32) - np.asarray(mean, dtype=np.float32)) / np.asarray(scale, dtype=np.float32)
    if not np.isfinite(normalized).all():
        raise ValueError("Normalized temporal sequences must be finite")
    return normalized.astype(np.float32)


def save_temporal_dataset(arrays: dict[str, np.ndarray], output: Path, *, random_state: int = RANDOM_STATE) -> tuple[Path, Path]:
    output = Path(output)
    train = arrays["split"] == "train"
    if not train.any():
        raise ValueError("Temporal dataset has no training rows")
    mean, scale = fit_normalization(arrays["X"][train])
    stored = dict(arrays)
    stored["X"] = normalize_sequences(arrays["X"], mean, scale)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, **stored)
    metadata = {
        "schema_version": "1.0",
        "window_size": WINDOW_SIZE,
        "tick_rate": TICK_RATE,
        "channels": TEMPORAL_CHANNELS,
        "normalization": {"mean": mean.tolist(), "scale": scale.tolist(), "fit_split": "train"},
        "random_state": random_state,
        "counts": {name: int((stored["split"] == name).sum()) for name in ("train", "validation", "test")},
    }
    metadata_path = output.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return output, metadata_path


def load_temporal_dataset(path: str | Path) -> tuple[dict[str, np.ndarray], dict]:
    path = Path(path)
    with np.load(path, allow_pickle=False) as data:
        arrays = {key: data[key] for key in data.files}
    metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if arrays["X"].ndim != 3 or arrays["X"].shape[1:] != (WINDOW_SIZE, len(TEMPORAL_CHANNELS)):
        raise ValueError("Invalid temporal dataset dimensions")
    return arrays, metadata


def train_temporal_baselines(arrays: dict[str, np.ndarray], random_state: int = RANDOM_STATE) -> dict:
    train = arrays["split"] == "train"
    X = arrays["X"][train].reshape(train.sum(), -1)
    y = arrays["y"][train]
    models = {
        "dummy": DummyClassifier(strategy="prior"),
        "logistic_regression": Pipeline((
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1000, random_state=random_state)),
        )),
    }
    for model in models.values():
        model.fit(X, y)
    return models


def temporal_metrics(arrays: dict[str, np.ndarray], probabilities, split: str) -> dict:
    selected = arrays["split"] == split
    scores = np.asarray(probabilities, dtype=float)
    if scores.shape != (int(selected.sum()),) or not np.isfinite(scores).all():
        raise ValueError("Temporal probabilities do not match selected split")
    targets = arrays["y"][selected]
    window = evaluate_predictions(pd.Series(targets), scores >= 0.5, scores)
    frame = pd.DataFrame({
        "match_id": arrays["match_id"][selected],
        "player_id": arrays["player_id"][selected],
        "label": np.where(targets == 1, "suspicious", "legitimate"),
    })
    players = aggregate_player_scores(frame, scores, "score")
    player_targets = players["label"].map(LABEL_TO_TARGET)
    if set(player_targets) != {0, 1}:
        raise ValueError("Both player target classes are required")
    return {
        "window": window,
        "player": {
            "roc_auc": float(roc_auc_score(player_targets, players["score"])),
            "pr_auc": float(average_precision_score(player_targets, players["score"])),
        },
    }


def save_baseline_bundle(model, metadata: dict, path: str | Path) -> tuple[Path, Path]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    metadata_path = path.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return path, metadata_path


def benchmark_summary(samples: list[float]) -> dict[str, float]:
    values = np.asarray(samples, dtype=float)
    if values.size == 0 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Benchmark samples must be finite non-negative values")
    return {"median_seconds": float(np.median(values)), "p95_seconds": float(np.percentile(values, 95))}


def paired_match_bootstrap_difference(match_ids, y_true, first, second, *, metric: str, iterations: int = 1000, random_state: int = RANDOM_STATE) -> dict:
    """Paired bootstrap that resamples whole matches, preserving player clusters."""
    match_ids = np.asarray(match_ids).astype(str)
    y_true = np.asarray(y_true)
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    if not (len(match_ids) == len(y_true) == len(first) == len(second)) or len(y_true) == 0:
        raise ValueError("Paired match bootstrap arrays must have equal non-zero length")
    scorer = average_precision_score if metric == "pr_auc" else roc_auc_score if metric == "roc_auc" else None
    if scorer is None:
        raise ValueError("metric must be pr_auc or roc_auc")
    matches = np.unique(match_ids)
    rng = np.random.default_rng(random_state)
    differences = []
    for _ in range(iterations):
        sampled = rng.choice(matches, size=len(matches), replace=True)
        indices = np.concatenate([np.flatnonzero(match_ids == match) for match in sampled])
        if np.unique(y_true[indices]).size != 2:
            continue
        differences.append(scorer(y_true[indices], first[indices]) - scorer(y_true[indices], second[indices]))
    if not differences:
        raise ValueError("Bootstrap match samples never contained both classes")
    return {
        "difference": float(scorer(y_true, first) - scorer(y_true, second)),
        "ci95": [float(np.percentile(differences, 2.5)), float(np.percentile(differences, 97.5))],
        "iterations": len(differences),
        "resampling_unit": "match",
    }
