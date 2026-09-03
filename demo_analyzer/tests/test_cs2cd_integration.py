import json

import pandas as pd

from cs2guard_demo.dataset.adapters.cs2cd import CS2CDAdapter
from cs2guard_demo.dataset.builder import DatasetBuilder
from cs2guard_demo.dataset.schema import validate_event_schema, validate_tick_schema


def test_cs2cd_to_aim_features_integration(tmp_path, monkeypatch):
    json_path = tmp_path / "match.json"
    parquet_path = tmp_path / "match.parquet"

    data = {
        "weapon_fire": [
            {"tick": 131, "user_steamid": "Player_1", "weapon": "ak47"},
            {"tick": 231, "user_steamid": "Player_3", "weapon": "deagle"},
        ],
        "cheaters": [{"steamid": "Player_3"}],
        "CSstats_info": [
            {
                "map": "de_mirage",
                "server": "eu_north Server",
                "avg_rank": "Gold Nova Master",
                "match_making_type": "Official Matchmaking",
            }
        ],
    }

    json_path.write_text(json.dumps(data), encoding="utf-8")
    parquet_path.touch()

    tick_rows = []

    for tick in range(100, 132):
        tick_rows.append(
            {
                "tick": tick,
                "steamid": "Player_1",
                "X": float(tick),
                "Y": 0.0,
                "Z": 0.0,
                "yaw": float(tick - 100),
                "pitch": float(tick - 100) * 0.25,
                "active_weapon_name": "ak47",
            }
        )

    for tick in range(200, 232):
        tick_rows.append(
            {
                "tick": tick,
                "steamid": "Player_3",
                "X": float(tick),
                "Y": 0.0,
                "Z": 0.0,
                "yaw": float(tick - 200) * 2.0,
                "pitch": float(tick - 200) * 0.5,
                "active_weapon_name": "deagle",
            }
        )

    fake_ticks = pd.DataFrame(tick_rows)
    monkeypatch.setattr(pd, "read_parquet", lambda _: fake_ticks)

    adapter = CS2CDAdapter(json_path, parquet_path)
    events = adapter.get_events()
    ticks = adapter.get_ticks()

    validate_event_schema(events)
    validate_tick_schema(ticks)

    builder = DatasetBuilder()
    windows = builder.build_canonical_temporal_windows(ticks, events, window_size=32)
    features = builder.build_aim_features(windows)

    assert windows["window_id"].nunique() == 2
    assert len(windows) == 64
    assert len(features) == 2
    assert features["window_id"].nunique() == 2

    assert set(features["source"]) == {"cs2cd"}
    assert set(features["source_player_id"]) == {"Player_1", "Player_3"}
    assert set(features["identity_scope"]) == {"match"}

    legitimate = features[features["source_player_id"] == "Player_1"].iloc[0]
    suspicious = features[features["source_player_id"] == "Player_3"].iloc[0]

    assert legitimate["label"] == "legitimate"
    assert suspicious["label"] == "suspicious"

    assert legitimate["player_id"] == f"cs2cd:{adapter.match_id}:Player_1"
    assert suspicious["player_id"] == f"cs2cd:{adapter.match_id}:Player_3"
    assert legitimate["player_id"] != suspicious["player_id"]

    feature_columns = [
        "mean_angular_speed",
        "max_angular_speed",
        "std_angular_speed",
        "mean_angular_acceleration",
        "max_angular_acceleration",
        "std_angular_acceleration",
    ]

    assert features[feature_columns].notna().all().all()