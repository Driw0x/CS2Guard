from pathlib import Path
import pandas as pd

import cs2guard_demo.dataset.adapters.demo as demo_module
from cs2guard_demo.dataset.adapters.demo import DemoAdapter
from cs2guard_demo.dataset.builder import DatasetBuilder
from cs2guard_demo.dataset.schema import validate_aim_feature_schema, validate_event_schema, validate_tick_schema


class FakeDemoParser:

    def __init__(self, demo_path: Path):
        self.demo_path = demo_path

    def get_match_metadata(self) -> dict:
        return {
            "map_name": "de_mirage",
            "patch_version": 12345,
            "demo_version": "valve_demo_2",
        }

    def get_player_ticks_df(self) -> pd.DataFrame:
        rows = []

        for tick in range(100, 132):
            rows.append({
                "tick": tick,
                "steamid": 76561198000000001,
                "name": "PlayerOne",
                "X": float(tick),
                "Y": 10.0,
                "Z": 20.0,
                "yaw": float(tick - 100),
                "pitch": float(tick - 100) * 0.5,
                "active_weapon_name": "ak47",
            })

        return pd.DataFrame(rows)

    def get_shots(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "tick": 131,
            "user_steamid": 76561198000000001,
            "user_name": "PlayerOne",
            "weapon": "ak47",
        }])

    def get_hits(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "tick": 131,
            "attacker_steamid": 76561198000000001,
            "attacker_name": "PlayerOne",
            "user_steamid": 76561198000000002,
            "user_name": "PlayerTwo",
            "weapon": "ak47",
            "dmg_health": 30,
            "dmg_armor": 5,
            "health": 70,
            "armor": 95,
            "hitgroup": "chest",
        }])

    def get_kills(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "tick": 131,
            "attacker_steamid": 76561198000000001,
            "attacker_name": "PlayerOne",
            "user_steamid": 76561198000000002,
            "user_name": "PlayerTwo",
            "weapon": "ak47",
            "headshot": True,
            "distance": 250.0,
            "hitgroup": "head",
            "noscope": False,
            "penetrated": 0,
            "thrusmoke": False,
        }])


def test_demo_adapter_canonical_schema(tmp_path, monkeypatch):
    demo_path = tmp_path / "match.dem"
    demo_path.touch()

    monkeypatch.setattr(demo_module, "DemoParser", FakeDemoParser)

    adapter = DemoAdapter(demo_path)
    ticks = adapter.get_ticks()
    events = adapter.get_events()

    validate_tick_schema(ticks)
    validate_event_schema(events)

    assert adapter.match_id == "match"
    assert set(ticks["source"]) == {"demo"}
    assert set(ticks["identity_scope"]) == {"global"}
    assert ticks["label"].isna().all()

    assert ticks.iloc[0]["source_player_id"] == "76561198000000001"
    assert ticks.iloc[0]["player_id"] == "demo:76561198000000001"

    assert len(events) == 3
    assert set(events["event_type"]) == {"shot", "hit", "kill"}
    assert set(events["player_id"]) == {"demo:76561198000000001"}

    hit = events[events["event_type"] == "hit"].iloc[0]
    kill = events[events["event_type"] == "kill"].iloc[0]

    assert hit["victim_id"] == "demo:76561198000000002"
    assert kill["victim_id"] == "demo:76561198000000002"


def test_demo_adapter_to_aim_features(tmp_path, monkeypatch):
    demo_path = tmp_path / "match.dem"
    demo_path.touch()

    monkeypatch.setattr(demo_module, "DemoParser", FakeDemoParser)

    adapter = DemoAdapter(demo_path)
    ticks = adapter.get_ticks()
    events = adapter.get_events()

    builder = DatasetBuilder()
    windows = builder.build_canonical_temporal_windows(ticks, events, window_size=32)
    features = builder.build_aim_features(windows)

    validate_aim_feature_schema(features)

    assert len(windows) == 32
    assert windows["window_id"].nunique() == 1
    assert len(features) == 1

    feature = features.iloc[0]

    assert feature["source"] == "demo"
    assert feature["match_id"] == "match"
    assert feature["source_player_id"] == "76561198000000001"
    assert feature["player_id"] == "demo:76561198000000001"
    assert feature["identity_scope"] == "global"
    assert pd.isna(feature["label"])

    feature_columns = [
        "mean_angular_speed",
        "max_angular_speed",
        "std_angular_speed",
        "mean_angular_acceleration",
        "max_angular_acceleration",
        "std_angular_acceleration",
    ]

    assert features[feature_columns].notna().all().all()