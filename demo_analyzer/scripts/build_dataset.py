from pathlib import Path
import pandas as pd

from cs2guard_demo.dataset.adapters.cs2cd import CS2CDAdapter
from cs2guard_demo.dataset.adapters.demo import DemoAdapter
from cs2guard_demo.dataset.builder import DatasetBuilder
from cs2guard_demo.dataset.schema import validate_aim_feature_schema, validate_event_schema, validate_tick_schema

DEMO_DIRECTORY = Path("data/raw/train_sources/demo")
CS2CD_DIRECTORY = Path("data/raw/train_sources/cs2cd")
OUTPUT_DIRECTORY = Path("data/processed")


def build_demo_dataset() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    builder = DatasetBuilder()
    all_events = []
    all_ticks = []
    all_windows = []
    all_features = []

    demo_files = sorted(DEMO_DIRECTORY.glob("*.dem"))

    for demo_path in demo_files:
        print(f"Processing demo: {demo_path.name}")

        adapter = DemoAdapter(demo_path)
        events = adapter.get_events()
        ticks = adapter.get_ticks()
        windows = builder.build_canonical_temporal_windows(ticks, events, window_size=32)
        features = builder.build_aim_features(windows)

        all_events.append(events)
        all_ticks.append(ticks)
        all_windows.append(windows)
        all_features.append(features)

    return _concat(all_events), _concat(all_ticks), _concat(all_windows), _concat(all_features)


def build_cs2cd_dataset() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    builder = DatasetBuilder()
    all_events = []
    all_ticks = []
    all_windows = []
    all_features = []

    for json_path in sorted(CS2CD_DIRECTORY.rglob("*.json")):
        parquet_path = json_path.with_suffix(".parquet")

        if not parquet_path.exists():
            print(f"Skipping {json_path.name}: matching parquet file not found.")
            continue

        print(f"Processing CS2CD: {json_path}")

        adapter = CS2CDAdapter(json_path, parquet_path)
        events = adapter.get_events()
        ticks = adapter.get_ticks()
        windows = builder.build_canonical_temporal_windows(ticks, events, window_size=32)
        features = builder.build_aim_features(windows)

        all_events.append(events)
        all_ticks.append(ticks)
        all_windows.append(windows)
        all_features.append(features)

    return _concat(all_events), _concat(all_ticks), _concat(all_windows), _concat(all_features)


def _concat(dataframes: list[pd.DataFrame]) -> pd.DataFrame:
    dataframes = [dataframe for dataframe in dataframes if not dataframe.empty]

    if not dataframes:
        return pd.DataFrame()

    return pd.concat(dataframes, ignore_index=True)


def main() -> None:
    demo_events, demo_ticks, demo_windows, demo_features = build_demo_dataset()
    cs2cd_events, cs2cd_ticks, cs2cd_windows, cs2cd_features = build_cs2cd_dataset()

    events = _concat([demo_events, cs2cd_events])
    ticks = _concat([demo_ticks, cs2cd_ticks])
    windows = _concat([demo_windows, cs2cd_windows])
    features = _concat([demo_features, cs2cd_features])

    if not events.empty:
        validate_event_schema(events)

    if not ticks.empty:
        validate_tick_schema(ticks)

    if not features.empty:
        validate_aim_feature_schema(features)

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    events.to_csv(OUTPUT_DIRECTORY / "events.csv", index=False)
    ticks.to_csv(OUTPUT_DIRECTORY / "ticks.csv", index=False)
    windows.to_csv(OUTPUT_DIRECTORY / "temporal_windows.csv", index=False)
    features.to_csv(OUTPUT_DIRECTORY / "aim_features.csv", index=False)

    print()
    print("=== CANONICAL DATASET ===")
    print(f"Sources: {sorted(events['source'].unique()) if not events.empty else []}")
    print(f"Matches: {events['match_id'].nunique() if not events.empty else 0}")
    print(f"Players: {events['player_id'].nunique() if not events.empty else 0}")
    print(f"Events: {len(events)}")
    print(f"Ticks: {len(ticks)}")
    print(f"Windows: {windows['window_id'].nunique() if not windows.empty else 0}")
    print(f"Aim features: {len(features)}")

    print()
    print(f"Events saved to: {OUTPUT_DIRECTORY / 'events.csv'}")
    print(f"Ticks saved to: {OUTPUT_DIRECTORY / 'ticks.csv'}")
    print(f"Temporal windows saved to: {OUTPUT_DIRECTORY / 'temporal_windows.csv'}")
    print(f"Aim features saved to: {OUTPUT_DIRECTORY / 'aim_features.csv'}")


if __name__ == "__main__":
    main()