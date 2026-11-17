"""Train, select, evaluate, benchmark, and explain M7 temporal models."""

import argparse
import json
import platform
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from cs2guard_demo.detection.anomaly import prepare_features
from cs2guard_demo.supervised import LABEL_TO_TARGET, aggregate_player_scores
from cs2guard_demo.temporal import (
    TEMPORAL_CHANNELS, TICK_RATE, WINDOW_SIZE, load_temporal_dataset,
    paired_match_bootstrap_difference, save_baseline_bundle, temporal_metrics,
    train_temporal_baselines,
)
from cs2guard_demo.temporal_models import (
    benchmark_model, occlusion_importance, predict_probabilities,
    save_temporal_bundle, train_temporal_model,
)


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "data" / "processed" / "temporal_dataset.npz")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "processed" / "m7_temporal")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=("cnn1d", "lstm", "gru", "transformer"),
        default=("cnn1d", "lstm", "gru", "transformer"),
    )
    parser.add_argument("--m5-model", type=Path)
    parser.add_argument("--m5-features", type=Path, default=ROOT / "data" / "processed" / "supervised_dataset.csv")
    return parser.parse_args()


def _probabilities(model, arrays, split, device=None):
    selected = arrays["split"] == split
    if hasattr(model, "predict_proba"):
        return model.predict_proba(arrays["X"][selected].reshape(selected.sum(), -1))[:, 1]
    return predict_probabilities(model, arrays["X"][selected], device=device)


def _player_frame(arrays, probabilities, split):
    selected = arrays["split"] == split
    frame = pd.DataFrame({
        "match_id": arrays["match_id"][selected], "player_id": arrays["player_id"][selected],
        "label": np.where(arrays["y"][selected] == 1, "suspicious", "legitimate"),
    })
    return aggregate_player_scores(frame, probabilities, "score")


def _hit_at(players, k):
    hits, matches = 0, 0
    for _, group in players.groupby("match_id"):
        if "suspicious" not in set(group["label"]):
            continue
        matches += 1
        hits += bool((group.sort_values(["score", "player_id"], ascending=[False, True]).head(k)["label"] == "suspicious").any())
    return {"hits": hits, "matches": matches, "rate": hits / matches if matches else None}


def _plot_explanation(sequence, importance, path):
    figure, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    axes[0].plot(sequence)
    axes[0].legend(TEMPORAL_CHANNELS, fontsize=7, ncol=3)
    axes[0].set_ylabel("Normalized value")
    axes[1].bar(np.arange(WINDOW_SIZE), importance)
    axes[1].set_ylabel("Score change")
    axes[1].set_xlabel("Window offset")
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)


def _m5_scores(path, features_path, arrays):
    model = joblib.load(path)
    features = pd.read_csv(features_path)
    lookup = features.set_index("window_id")
    selected = arrays["split"] == "test"
    ids = arrays["window_id"][selected]
    aligned = lookup.loc[ids]
    return model.predict_proba(prepare_features(aligned))[:, list(model.classes_).index(1)]


def main() -> None:
    args = parse_args()
    device = None if args.device == "auto" else args.device
    resolved_device = "cuda" if device is None and torch.cuda.is_available() else device or "cpu"
    args.output.mkdir(parents=True, exist_ok=True)
    arrays, dataset_metadata = load_temporal_dataset(args.dataset)
    candidates = {}
    validation = {}
    candidate_cost = {}

    baselines = train_temporal_baselines(arrays)
    for name, model in baselines.items():
        probabilities = _probabilities(model, arrays, "validation")
        validation[name] = temporal_metrics(arrays, probabilities, "validation")
        save_baseline_bundle(model, {"model_family": "temporal_baseline", "name": name, "validation": validation[name]}, args.output / f"{name}.joblib")

    for family in args.models:
        model, history = train_temporal_model(family, arrays, epochs=args.epochs, device=device)
        probabilities = _probabilities(model, arrays, "validation", resolved_device)
        validation[family] = temporal_metrics(arrays, probabilities, "validation")
        candidates[family] = model
        sample = arrays["X"][arrays["split"] == "validation"][:1]
        candidate_cost[family] = {
            "latency": benchmark_model(model, sample, repeats=20, warmups=5, device=resolved_device)["median_seconds"],
            "parameters": sum(value.numel() for value in model.parameters()),
        }
        metadata = {
            "model_family": "temporal", "model_name": family, "version": "v1", "architecture": family,
            "hidden_size": 32, "channels": TEMPORAL_CHANNELS, "window_size": WINDOW_SIZE, "tick_rate": TICK_RATE,
            "normalization": dataset_metadata["normalization"], "label_mapping": LABEL_TO_TARGET,
            "decision_threshold": None, "validation": validation[family], "history": history,
            "training_environment": {
                "device": resolved_device,
                "device_name": torch.cuda.get_device_name(0) if resolved_device == "cuda" else platform.processor(),
                "python": platform.python_version(), "platform": platform.platform(),
                "torch": torch.__version__, "rocm": torch.version.hip,
            },
        }
        save_temporal_bundle(model, metadata, args.output / f"{family}_v1.pt")

    best = min(candidates, key=lambda name: (
        -validation[name]["player"]["pr_auc"], -validation[name]["player"]["roc_auc"],
        candidate_cost[name]["latency"], candidate_cost[name]["parameters"], name,
    ))
    model = candidates[best]
    test_probabilities = _probabilities(model, arrays, "test", resolved_device)
    test_metrics = temporal_metrics(arrays, test_probabilities, "test")
    players = _player_frame(arrays, test_probabilities, "test")
    comparison = {
        "selection_metric": "validation player-match PR-AUC",
        "selected": best,
        "training_device": resolved_device,
        "validation": validation,
        "candidate_cost": candidate_cost,
        "test": {best: test_metrics},
        "hit_at_1": _hit_at(players, 1),
        "hit_at_3": _hit_at(players, 3),
    }
    baseline_test = _probabilities(baselines["logistic_regression"], arrays, "test")
    comparison["test"]["temporal_logistic_regression"] = temporal_metrics(arrays, baseline_test, "test")

    selected = arrays["split"] == "test"
    if args.m5_model:
        m5 = _m5_scores(args.m5_model, args.m5_features, arrays)
        comparison["test"]["m5_random_forest"] = temporal_metrics(arrays, m5, "test")
        temporal_players = _player_frame(arrays, test_probabilities, "test").sort_values(["match_id", "player_id"])
        m5_players = _player_frame(arrays, m5, "test").sort_values(["match_id", "player_id"])
        targets = temporal_players["label"].map(LABEL_TO_TARGET).to_numpy()
        comparison["paired_bootstrap"] = {
            metric: paired_match_bootstrap_difference(
                temporal_players["match_id"], targets, temporal_players["score"], m5_players["score"], metric=metric,
            )
            for metric in ("pr_auc", "roc_auc")
        }

    sample_one = arrays["X"][selected][:1]
    sample_batch = arrays["X"][selected][:256]
    comparison["benchmark_cpu"] = {
        "environment": {"python": platform.python_version(), "platform": platform.platform(), "torch": torch.__version__},
        "batch_1": benchmark_model(model, sample_one, device="cpu"),
        "batch_256": {**benchmark_model(model, sample_batch, device="cpu"), "samples": len(sample_batch)},
    }
    batch = comparison["benchmark_cpu"]["batch_256"]
    batch["throughput_samples_per_second"] = len(sample_batch) / batch["median_seconds"]
    if resolved_device == "cuda":
        comparison["benchmark_rocm"] = {
            "environment": {
                "device_name": torch.cuda.get_device_name(0), "torch": torch.__version__,
                "rocm": torch.version.hip,
            },
            "batch_1": benchmark_model(model, sample_one, device="cuda"),
            "batch_256": {**benchmark_model(model, sample_batch, device="cuda"), "samples": len(sample_batch)},
        }
        gpu_batch = comparison["benchmark_rocm"]["batch_256"]
        gpu_batch["throughput_samples_per_second"] = len(sample_batch) / gpu_batch["median_seconds"]
    top = np.argsort(test_probabilities)[-min(10, len(test_probabilities)):][::-1]
    explained = arrays["X"][selected][top]
    importance = occlusion_importance(model, explained, device=resolved_device)
    explanations = []
    test_ids = arrays["window_id"][selected]
    for rank, index in enumerate(top, 1):
        image = f"sequence_{rank:02d}.png"
        _plot_explanation(arrays["X"][selected][index], importance["by_step"][rank - 1], args.output / image)
        explanations.append({
            "window_id": str(test_ids[index]), "score": float(test_probabilities[index]), "plot": image,
            "step_importance": importance["by_step"][rank - 1].tolist(),
            "channel_importance": dict(zip(TEMPORAL_CHANNELS, map(float, importance["by_channel"][rank - 1]))),
        })
    comparison["explanations"] = explanations
    selected_metadata_path = args.output / f"{best}_v1.json"
    selected_metadata = json.loads(selected_metadata_path.read_text(encoding="utf-8"))
    selected_metadata.update({
        "selection": {
            "criterion": "validation player-match PR-AUC, then ROC-AUC, inference latency, parameter count, and name",
            "selected": True,
            "candidates": list(candidates),
        },
        "training_protocol": {
            "random_state": 42, "max_epochs": args.epochs, "early_stopping_patience": 3,
            "loss": "weighted BCEWithLogitsLoss", "train_sequences": int((arrays["split"] == "train").sum()),
            "validation_sequences": int((arrays["split"] == "validation").sum()),
            "test_sequences": int(selected.sum()), "test_locked_until_selection": True,
        },
        "test": comparison["test"],
        "hit_at_1": comparison["hit_at_1"],
        "hit_at_3": comparison["hit_at_3"],
        "benchmark_cpu": comparison["benchmark_cpu"],
    })
    if "paired_bootstrap" in comparison:
        selected_metadata["paired_bootstrap"] = comparison["paired_bootstrap"]
    if "benchmark_rocm" in comparison:
        selected_metadata["benchmark_rocm"] = comparison["benchmark_rocm"]
    selected_metadata_path.write_text(json.dumps(selected_metadata, indent=2), encoding="utf-8")
    (args.output / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    lines = ["# M7 temporal model comparison", "", f"Selected model: **{best}**", "", "Selection used validation player-match PR-AUC. Test remained locked until selection.", "", "## Test metrics", "", "```json", json.dumps(comparison["test"], indent=2), "```"]
    if "benchmark_rocm" in comparison:
        lines.extend(["", "## ROCm inference", "", "```json", json.dumps(comparison["benchmark_rocm"], indent=2), "```"])
    lines.extend(["", "## CPU inference", "", "```json", json.dumps(comparison["benchmark_cpu"], indent=2), "```", "", "Scores are uncalibrated model outputs, not proof of cheating. Occlusion importance is descriptive and not causal."])
    (args.output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Selected: {best}")
    print(f"Report: {args.output / 'report.md'}")


if __name__ == "__main__":
    main()
