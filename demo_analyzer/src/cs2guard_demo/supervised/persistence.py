import json
from pathlib import Path

import joblib


def save_model_bundle(
    model,
    metadata: dict,
    output_dir: Path,
    model_name: str,
    version: str,
) -> tuple[Path, Path]:
    if not model_name:
        raise ValueError("model_name must not be empty")
    if not version:
        raise ValueError("version must not be empty")

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{model_name}_{version}"
    model_path = output_dir / f"{stem}.joblib"
    metadata_path = output_dir / f"{stem}.json"

    joblib.dump(model, model_path)

    with metadata_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2, sort_keys=True)

    return model_path, metadata_path


def load_model_bundle(model_path: Path, metadata_path: Path) -> tuple[object, dict]:
    model = joblib.load(model_path)

    with metadata_path.open(encoding="utf-8") as file:
        metadata = json.load(file)

    return model, metadata