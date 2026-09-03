import argparse
from pathlib import Path
from cs2guard_demo.dataset.adapters.cs2cd import CS2CDAdapter
from cs2guard_demo.dataset.schema import validate_event_schema, validate_tick_schema
from cs2guard_demo.dataset.builder import DatasetBuilder


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('json_path', type=Path)
    parser.add_argument('parquet_path', type=Path)
    args = parser.parse_args()
    adapter = CS2CDAdapter(args.json_path, args.parquet_path)
    metadata = adapter.get_metadata()
    labels = adapter.get_labels()
    events = adapter.get_events()
    ticks = adapter.get_ticks()
    builder = DatasetBuilder()
    windows = builder.build_canonical_temporal_windows(ticks, events)
    features = builder.build_aim_features(windows)

    print()
    print('=== M2 FEATURES ===')
    print(f"Windows: {(windows['window_id'].nunique() if not windows.empty else 0)}")
    print(f'Window rows: {len(windows)}')
    print(f'Aim features: {len(features)}')
    print(f"Suspicious features: {((features['label'] == 'suspicious').sum() if not features.empty else 0)}")
    print(features.head().to_string(index=False))

    validate_event_schema(events)
    validate_tick_schema(ticks)

    print('=== CS2CD MATCH ===')
    print(f"Match ID: {metadata['match_id']}")
    print(f"Map: {metadata['map_name']}")
    print(f'Players: {len(labels)}')
    print(f'Events: {len(events)}')
    print(f'Ticks: {len(ticks)}')
    print()
    print('=== LABELS ===')
    print(labels[['source_player_id', 'player_id', 'label']].to_string(index=False))
    print()
    print('=== EVENT TYPES ===')
    print(events['event_type'].value_counts())
    print()
    print('=== SUSPICIOUS PLAYERS ===')

    suspicious = labels[labels['label'] == 'suspicious']

    print(suspicious[['source_player_id', 'player_id']].to_string(index=False))
    
    expected_cheaters = adapter.cheaters
    actual_cheaters = set(suspicious['source_player_id'])

    if actual_cheaters != expected_cheaters:
        raise RuntimeError(f'Label mismatch: expected {sorted(expected_cheaters)}, got {sorted(actual_cheaters)}')

    if ticks['player_id'].isna().any():
        raise RuntimeError('Missing canonical player IDs in tick data.')

    if events['player_id'].isna().any():
        raise RuntimeError('Missing canonical player IDs in event data.')

    if ticks['player_id'].duplicated().all():
        raise RuntimeError('Invalid canonical player identity mapping.')

    print()
    print('CS2CD canonical validation: PASS')

if __name__ == '__main__':
    main()
