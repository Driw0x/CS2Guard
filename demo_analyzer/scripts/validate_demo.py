from pathlib import Path

from cs2guard_demo.dataset.adapters.demo import DemoAdapter
from cs2guard_demo.dataset.builder import DatasetBuilder
from cs2guard_demo.dataset.schema import validate_aim_feature_schema, validate_event_schema, validate_tick_schema

DEMO_PATH = Path("data/raw/train_sources/demo/test.dem")


def main() -> None:
    adapter = DemoAdapter(DEMO_PATH)

    metadata = adapter.get_metadata()
    events = adapter.get_events()
    ticks = adapter.get_ticks()

    validate_event_schema(events)
    validate_tick_schema(ticks)

    builder = DatasetBuilder()
    windows = builder.build_canonical_temporal_windows(ticks, events, window_size=32)
    features = builder.build_aim_features(windows)

    if not features.empty:
        validate_aim_feature_schema(features)

    print("=== DEMO MATCH ===")
    print(f"Match ID: {adapter.match_id}")
    print(f"Map: {metadata.get('map_name')}")
    print(f"Players: {ticks['player_id'].nunique()}")
    print(f"Events: {len(events)}")
    print(f"Ticks: {len(ticks)}")

    print()
    print("Event types:")
    print(events["event_type"].value_counts().to_string())

    print()
    print("=== M2 FEATURES ===")
    print(f"Windows: {windows['window_id'].nunique() if not windows.empty else 0}")
    print(f"Window rows: {len(windows)}")
    print(f"Aim features: {len(features)}")

    if not features.empty:
        print()
        print(features.head().to_string(index=False))

    assert events["source"].eq("demo").all()
    assert ticks["source"].eq("demo").all()
    assert events["identity_scope"].eq("global").all()
    assert ticks["identity_scope"].eq("global").all()
    assert events["player_id"].notna().all()
    assert ticks["player_id"].notna().all()
    assert len(features) == windows["window_id"].nunique()

    print()
    print("Demo canonical validation: PASS")


if __name__ == "__main__":
    main()