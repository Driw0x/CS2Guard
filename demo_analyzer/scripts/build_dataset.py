import argparse
import gc
import json
from pathlib import Path

import pandas as pd

from cs2guard_demo.dataset.adapters.cs2cd import CS2CDAdapter
from cs2guard_demo.dataset.adapters.demo import DemoAdapter
from cs2guard_demo.dataset.builder import DatasetBuilder
from cs2guard_demo.dataset.schema import validate_aim_feature_schema, validate_event_schema, validate_tick_schema

DEMO_DIRECTORY = Path("data/raw/train_sources/demo")
CS2CD_DIRECTORY = Path("data/raw/train_sources/cs2cd")
OUTPUT_DIRECTORY = Path("data/processed")
CHECKPOINT_FILE = OUTPUT_DIRECTORY / ".build_checkpoint.json"
OUTPUT_FILES = {
    "events": "events.csv",
    "ticks": "ticks.csv",
    "windows": "temporal_windows.csv",
    "features": "aim_features.csv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", help="Resume an interrupted dataset build.")
    return parser.parse_args()


def source_key(source_type: str, path: Path) -> str:
    base = DEMO_DIRECTORY if source_type == "demo" else CS2CD_DIRECTORY
    return f"{source_type}:{path.relative_to(base).as_posix()}"


def empty_checkpoint() -> dict:
    return {
        "completed": [],
        "current": None,
        "counts": {"events": 0, "ticks": 0, "windows": 0, "features": 0},
        "sources": [],
        "matches": [],
        "players": [],
    }


def save_checkpoint(checkpoint: dict) -> None:
    temporary = CHECKPOINT_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")
    temporary.replace(CHECKPOINT_FILE)


def load_checkpoint() -> dict:
    if not CHECKPOINT_FILE.exists():
        return empty_checkpoint()

    return json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))


def output_path(name: str) -> Path:
    return OUTPUT_DIRECTORY / OUTPUT_FILES[name]


def get_output_sizes() -> dict[str, int]:
    return {name: output_path(name).stat().st_size if output_path(name).exists() else 0 for name in OUTPUT_FILES}


def rollback_current(checkpoint: dict) -> None:
    current = checkpoint.get("current")

    if not current:
        return

    print(f"Rolling back interrupted match: {current['source_key']}")

    for name, size in current["file_sizes"].items():
        path = output_path(name)

        if not path.exists():
            continue

        if size == 0:
            path.unlink()
        else:
            with path.open("r+b") as file:
                file.truncate(size)

    checkpoint["current"] = None
    save_checkpoint(checkpoint)


def prepare_build(resume: bool) -> dict:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if not resume:
        for name in OUTPUT_FILES:
            path = output_path(name)

            if path.exists():
                path.unlink()

        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()

        return empty_checkpoint()

    checkpoint = load_checkpoint()
    rollback_current(checkpoint)
    print(f"Resume enabled: {len(checkpoint['completed'])} completed match(es) found.")
    return checkpoint


def append_dataframe(name: str, dataframe: pd.DataFrame) -> None:
    path = output_path(name)
    header = not path.exists() or path.stat().st_size == 0
    dataframe.to_csv(path, mode="a", header=header, index=False)


def validate_chunk(events: pd.DataFrame, ticks: pd.DataFrame, features: pd.DataFrame) -> None:
    if not events.empty:
        validate_event_schema(events)

    if not ticks.empty:
        validate_tick_schema(ticks)

    if not features.empty:
        validate_aim_feature_schema(features)


def build_demo_chunk(builder: DatasetBuilder, demo_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    adapter = DemoAdapter(demo_path)
    events = adapter.get_events()
    ticks = adapter.get_ticks()
    windows = builder.build_canonical_temporal_windows(ticks, events, window_size=32)
    features = builder.build_aim_features(windows)
    return events, ticks, windows, features


def build_cs2cd_chunk(builder: DatasetBuilder, json_path: Path, parquet_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    adapter = CS2CDAdapter(json_path, parquet_path)
    events = adapter.get_events()
    ticks = adapter.get_ticks()
    windows = builder.build_canonical_temporal_windows(ticks, events, window_size=32)
    features = builder.build_aim_features(windows)
    return events, ticks, windows, features


def collect_sources() -> list[tuple[str, Path, Path | None]]:
    sources = []

    for demo_path in sorted(DEMO_DIRECTORY.glob("*.dem")):
        sources.append(("demo", demo_path, None))

    for json_path in sorted(CS2CD_DIRECTORY.rglob("*.json")):
        parquet_path = json_path.with_suffix(".parquet")

        if not parquet_path.exists():
            print(f"Skipping {json_path.name}: matching parquet file not found.")
            continue

        sources.append(("cs2cd", json_path, parquet_path))

    return sources


def update_checkpoint(checkpoint: dict, key: str, events: pd.DataFrame, ticks: pd.DataFrame, windows: pd.DataFrame, features: pd.DataFrame) -> None:
    checkpoint["completed"].append(key)
    checkpoint["counts"]["events"] += len(events)
    checkpoint["counts"]["ticks"] += len(ticks)
    checkpoint["counts"]["windows"] += windows["window_id"].nunique() if not windows.empty and "window_id" in windows.columns else 0
    checkpoint["counts"]["features"] += len(features)

    if not events.empty:
        checkpoint["sources"] = sorted(set(checkpoint["sources"]) | set(events["source"].dropna().astype(str)))
        checkpoint["matches"] = sorted(set(checkpoint["matches"]) | set(events["match_id"].dropna().astype(str)))
        checkpoint["players"] = sorted(set(checkpoint["players"]) | set(events["player_id"].dropna().astype(str)))

    checkpoint["current"] = None
    save_checkpoint(checkpoint)


def print_final_summary(checkpoint: dict) -> None:
    counts = checkpoint["counts"]

    print()
    print("=== CANONICAL DATASET ===")
    print(f"Sources: {checkpoint['sources']}")
    print(f"Matches: {len(checkpoint['matches'])}")
    print(f"Players: {len(checkpoint['players'])}")
    print(f"Events: {counts['events']}")
    print(f"Ticks: {counts['ticks']}")
    print(f"Windows: {counts['windows']}")
    print(f"Aim features: {counts['features']}")
    print()
    print(f"Events saved to: {output_path('events')}")
    print(f"Ticks saved to: {output_path('ticks')}")
    print(f"Temporal windows saved to: {output_path('windows')}")
    print(f"Aim features saved to: {output_path('features')}")


def main() -> None:
    args = parse_args()
    builder = DatasetBuilder()
    sources = collect_sources()
    checkpoint = prepare_build(args.resume)
    completed = set(checkpoint["completed"])

    for source_type, path, extra_path in sources:
        key = source_key(source_type, path)

        if key in completed:
            print(f"Skipping completed: {path.name}")
            continue

        checkpoint["current"] = {"source_key": key, "file_sizes": get_output_sizes()}
        save_checkpoint(checkpoint)
        print(f"Processing {source_type}: {path}")

        if source_type == "demo":
            events, ticks, windows, features = build_demo_chunk(builder, path)
        else:
            assert extra_path is not None
            events, ticks, windows, features = build_cs2cd_chunk(builder, path, extra_path)

        validate_chunk(events, ticks, features)
        append_dataframe("events", events)
        append_dataframe("ticks", ticks)
        append_dataframe("windows", windows)
        append_dataframe("features", features)
        update_checkpoint(checkpoint, key, events, ticks, windows, features)
        completed.add(key)

        del events, ticks, windows, features
        gc.collect()

    print_final_summary(checkpoint)
    CHECKPOINT_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()