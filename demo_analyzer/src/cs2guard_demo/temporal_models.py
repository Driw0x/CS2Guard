"""Small PyTorch sequence models and training helpers for M7."""

from __future__ import annotations

import json
from pathlib import Path
import time

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from cs2guard_demo.supervised import LABEL_TO_TARGET
from cs2guard_demo.temporal import RANDOM_STATE, TEMPORAL_CHANNELS, TICK_RATE, WINDOW_SIZE, temporal_metrics


class CNN1D(nn.Module):
    def __init__(self, channels: int = len(TEMPORAL_CHANNELS), hidden_size: int = 32):
        super().__init__()
        self.network = nn.Sequential(
            nn.Conv1d(channels, hidden_size, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(1),
            nn.Flatten(),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, values):
        return self.network(values.transpose(1, 2)).squeeze(1)


class RecurrentModel(nn.Module):
    def __init__(self, kind: str, channels: int = len(TEMPORAL_CHANNELS), hidden_size: int = 32):
        super().__init__()
        recurrent = nn.LSTM if kind == "lstm" else nn.GRU if kind == "gru" else None
        if recurrent is None:
            raise ValueError("Recurrent kind must be lstm or gru")
        self.recurrent = recurrent(channels, hidden_size, batch_first=True)
        self.output = nn.Linear(hidden_size, 1)

    def forward(self, values):
        output, _ = self.recurrent(values)
        return self.output(output[:, -1]).squeeze(1)


class TransformerModel(nn.Module):
    def __init__(self, channels: int = len(TEMPORAL_CHANNELS), hidden_size: int = 32):
        super().__init__()
        self.input = nn.Linear(channels, hidden_size)
        self.position = nn.Parameter(torch.zeros(1, WINDOW_SIZE, hidden_size))
        layer = nn.TransformerEncoderLayer(hidden_size, nhead=4, dim_feedforward=hidden_size * 2, dropout=0.1, batch_first=True)
        self.encoder = nn.TransformerEncoder(layer, num_layers=1)
        self.output = nn.Linear(hidden_size, 1)

    def forward(self, values):
        encoded = self.encoder(self.input(values) + self.position[:, : values.shape[1]])
        return self.output(encoded.mean(dim=1)).squeeze(1)


def create_temporal_model(family: str, *, channels: int = len(TEMPORAL_CHANNELS), hidden_size: int = 32) -> nn.Module:
    if family == "cnn1d":
        return CNN1D(channels, hidden_size)
    if family in {"lstm", "gru"}:
        return RecurrentModel(family, channels, hidden_size)
    if family == "transformer":
        return TransformerModel(channels, hidden_size)
    raise ValueError(f"Unknown temporal model family: {family}")


def _device(requested: str | None = None) -> torch.device:
    if requested:
        device = torch.device(requested)
        if device.type == "cuda" and not torch.cuda.is_available():
            raise ValueError("CUDA was requested but is unavailable")
        return device
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def predict_probabilities(model: nn.Module, sequences: np.ndarray, *, batch_size: int = 256, device: str | None = None) -> np.ndarray:
    target = _device(device)
    model = model.to(target).eval()
    loader = DataLoader(TensorDataset(torch.as_tensor(sequences, dtype=torch.float32)), batch_size=batch_size)
    probabilities = []
    with torch.no_grad():
        for (values,) in loader:
            probabilities.append(torch.sigmoid(model(values.to(target))).cpu().numpy())
    return np.concatenate(probabilities) if probabilities else np.empty(0, dtype=float)


def train_temporal_model(
    family: str,
    arrays: dict[str, np.ndarray],
    *,
    epochs: int = 20,
    patience: int = 3,
    batch_size: int = 256,
    learning_rate: float = 1e-3,
    random_state: int = RANDOM_STATE,
    device: str | None = None,
) -> tuple[nn.Module, list[dict]]:
    if epochs <= 0 or patience <= 0:
        raise ValueError("epochs and patience must be positive")
    torch.manual_seed(random_state)
    np.random.seed(random_state)
    target = _device(device)
    model = create_temporal_model(family).to(target)
    train = arrays["split"] == "train"
    validation = arrays["split"] == "validation"
    if not train.any() or not validation.any():
        raise ValueError("Temporal training requires train and validation rows")
    positives = int(arrays["y"][train].sum())
    negatives = int(train.sum()) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("Temporal training requires both classes")
    criterion = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([negatives / positives], device=target))
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    generator = torch.Generator().manual_seed(random_state)
    loader = DataLoader(
        TensorDataset(torch.as_tensor(arrays["X"][train], dtype=torch.float32), torch.as_tensor(arrays["y"][train], dtype=torch.float32)),
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
    )
    best_state, best_score, stale, history = None, -np.inf, 0, []
    for epoch in range(1, epochs + 1):
        model.train()
        losses = []
        for values, labels in loader:
            optimizer.zero_grad()
            loss = criterion(model(values.to(target)), labels.to(target))
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        probabilities = predict_probabilities(model, arrays["X"][validation], device=str(target))
        metrics = temporal_metrics(arrays, probabilities, "validation")
        score = metrics["player"]["pr_auc"]
        history.append({"epoch": epoch, "loss": float(np.mean(losses)), "validation": metrics})
        if score > best_score:
            best_score, stale = score, 0
            best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
        else:
            stale += 1
            if stale >= patience:
                break
    model.load_state_dict(best_state)
    return model.cpu(), history


def save_temporal_bundle(model: nn.Module, metadata: dict, path: str | Path) -> tuple[Path, Path]:
    path = Path(path)
    if path.suffix != ".pt":
        raise ValueError("Temporal model path must use .pt")
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), path)
    metadata_path = path.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return path, metadata_path


def load_temporal_bundle(path: str | Path) -> tuple[nn.Module, dict]:
    path = Path(path)
    metadata = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if metadata.get("model_family") != "temporal":
        raise ValueError("Temporal metadata requires model_family=temporal")
    if metadata.get("channels") != TEMPORAL_CHANNELS:
        raise ValueError("Temporal metadata channel order is incompatible")
    if metadata.get("window_size") != WINDOW_SIZE:
        raise ValueError("Temporal metadata window_size must be 32")
    if metadata.get("tick_rate") != TICK_RATE:
        raise ValueError("Temporal metadata tick_rate must be 64 Hz")
    if metadata.get("label_mapping") != LABEL_TO_TARGET:
        raise ValueError("Temporal metadata label mapping is incompatible")
    for key in ("model_name", "version"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"Temporal metadata requires {key}")
    normalization = metadata.get("normalization")
    if not isinstance(normalization, dict):
        raise ValueError("Temporal metadata requires normalization")
    mean = np.asarray(normalization.get("mean"), dtype=float)
    scale = np.asarray(normalization.get("scale"), dtype=float)
    if mean.shape != (len(TEMPORAL_CHANNELS),) or scale.shape != mean.shape or not np.isfinite(mean).all() or not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError("Temporal normalization must contain six finite means and positive scales")
    model = create_temporal_model(metadata["architecture"], hidden_size=int(metadata.get("hidden_size", 32)))
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    return model.eval(), metadata


def occlusion_importance(model: nn.Module, sequences: np.ndarray, *, device: str | None = None) -> dict[str, np.ndarray]:
    """Score changes when each time step or channel is replaced by normalized zero."""
    values = np.asarray(sequences, dtype=np.float32)
    baseline = predict_probabilities(model, values, device=device)
    by_step = np.empty((len(values), values.shape[1]), dtype=np.float32)
    by_channel = np.empty((len(values), values.shape[2]), dtype=np.float32)
    for index in range(values.shape[1]):
        occluded = values.copy()
        occluded[:, index, :] = 0
        by_step[:, index] = baseline - predict_probabilities(model, occluded, device=device)
    for index in range(values.shape[2]):
        occluded = values.copy()
        occluded[:, :, index] = 0
        by_channel[:, index] = baseline - predict_probabilities(model, occluded, device=device)
    return {"baseline": baseline, "by_step": by_step, "by_channel": by_channel}


def benchmark_model(
    model: nn.Module,
    sample: np.ndarray,
    *,
    repeats: int = 100,
    warmups: int = 20,
    device: str | None = None,
) -> dict:
    target = _device(device)
    model = model.to(target).eval()
    tensor = torch.as_tensor(sample, dtype=torch.float32, device=target)

    def synchronize() -> None:
        if target.type == "cuda":
            torch.cuda.synchronize(target)

    with torch.no_grad():
        for _ in range(warmups):
            model(tensor)
        synchronize()
        durations = []
        for _ in range(repeats):
            start = time.perf_counter()
            model(tensor)
            synchronize()
            durations.append(time.perf_counter() - start)
    values = np.asarray(durations)
    return {
        "device": str(target),
        "median_seconds": float(np.median(values)),
        "p95_seconds": float(np.percentile(values, 95)),
        "repeats": repeats,
    }
