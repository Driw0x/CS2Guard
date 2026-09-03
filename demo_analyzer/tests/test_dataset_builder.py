import math

import pandas as pd

from cs2guard_demo.dataset.builder import (
    DatasetBuilder,
    is_ignored_weapon,
    is_valid_player,
    safe_float,
    safe_int,
)

from cs2guard_demo.dataset.normalization import AIM_FEATURE_COLUMNS, fit_normalization_stats, normalize_features

from cs2guard_demo.dataset.labels import apply_labels, validate_labels

from cs2guard_demo.dataset.splitting import (
    build_leakage_groups,
    create_dataset_splits,
    validate_no_data_leakage,
)

from cs2guard_demo.dataset.statistics import generate_dataset_statistics


class FakeDemoParser:
    def __init__(self, demo_path):
        self.demo_path = demo_path

    def get_match_metadata(self):
        return {
            "map_name": "de_test",
            "patch_version": "test_patch",
            "demo_version": "test_demo",
        }

    def get_shots(self):
        return pd.DataFrame(
            [
                {
                    "tick": 40,
                    "user_steamid": 1,
                    "user_name": "PlayerOne",
                    "weapon": "weapon_ak47",
                },
                {
                    "tick": 50,
                    "user_steamid": 2,
                    "user_name": "PlayerTwo",
                    "weapon": "weapon_m4a1",
                },
                {
                    "tick": 55,
                    "user_steamid": 1,
                    "user_name": "PlayerOne",
                    "weapon": "weapon_flashbang",
                },
                {
                    "tick": 56,
                    "user_steamid": 2,
                    "user_name": "PlayerTwo",
                    "weapon": "weapon_knife",
                },
            ]
        )

    def get_hits(self):
        return pd.DataFrame(
            [
                {
                    "tick": 40,
                    "attacker_steamid": 1,
                    "attacker_name": "PlayerOne",
                    "user_steamid": 2,
                    "user_name": "PlayerTwo",
                    "weapon": "weapon_ak47",
                    "dmg_health": 30,
                    "dmg_armor": 5,
                    "health": 70,
                    "armor": 95,
                    "hitgroup": "chest",
                },
                {
                    "tick": 50,
                    "attacker_steamid": 2,
                    "attacker_name": "PlayerTwo",
                    "user_steamid": 1,
                    "user_name": "PlayerOne",
                    "weapon": "weapon_m4a1",
                    "dmg_health": 40,
                    "dmg_armor": 0,
                    "health": 60,
                    "armor": 0,
                    "hitgroup": "head",
                },
                {
                    "tick": 45,
                    "attacker_steamid": 1,
                    "attacker_name": "PlayerOne",
                    "user_steamid": 1,
                    "user_name": "PlayerOne",
                    "weapon": "",
                    "dmg_health": 1,
                    "dmg_armor": 0,
                    "health": 0,
                    "armor": 0,
                    "hitgroup": "generic",
                },
            ]
        )

    def get_kills(self):
        return pd.DataFrame(
            [
                {
                    "tick": 40,
                    "attacker_steamid": 1,
                    "attacker_name": "PlayerOne",
                    "user_steamid": 2,
                    "user_name": "PlayerTwo",
                    "weapon": "weapon_ak47",
                    "headshot": False,
                    "distance": 500.0,
                    "hitgroup": "chest",
                    "noscope": False,
                    "penetrated": 0,
                    "thrusmoke": False,
                },
                {
                    "tick": 50,
                    "attacker_steamid": 2,
                    "attacker_name": "PlayerTwo",
                    "user_steamid": 1,
                    "user_name": "PlayerOne",
                    "weapon": "weapon_m4a1",
                    "headshot": True,
                    "distance": 250.0,
                    "hitgroup": "head",
                    "noscope": False,
                    "penetrated": 1,
                    "thrusmoke": False,
                },
            ]
        )

    def get_player_ticks_df(self):
        rows = []

        for steamid, name in [(1, "PlayerOne"), (2, "PlayerTwo")]:
            for tick in range(1, 65):
                rows.append(
                    {
                        "tick": tick,
                        "steamid": steamid,
                        "name": name,
                        "team_name": "TERRORIST" if steamid == 1 else "CT",
                        "X": float(tick),
                        "Y": float(tick * 2),
                        "Z": 64.0,
                        "yaw": float(tick),
                        "pitch": float(tick) * 0.25,
                    }
                )

        return pd.DataFrame(rows)


def create_fake_demos(tmp_path):
    demo_a = tmp_path / "match_a.dem"
    demo_b = tmp_path / "match_b.dem"

    demo_a.touch()
    demo_b.touch()

    return demo_a, demo_b


def test_process_multiple_demos(monkeypatch, tmp_path):
    monkeypatch.setattr("cs2guard_demo.dataset.builder.DemoParser", FakeDemoParser)
    create_fake_demos(tmp_path)

    builder = DatasetBuilder()
    builder.process_directory(tmp_path)

    dataset = builder.build()

    assert dataset["match_id"].nunique() == 2
    assert set(dataset["match_id"]) == {"match_a", "match_b"}


def test_event_level_samples(monkeypatch, tmp_path):
    monkeypatch.setattr("cs2guard_demo.dataset.builder.DemoParser", FakeDemoParser)
    create_fake_demos(tmp_path)

    builder = DatasetBuilder()
    builder.process_directory(tmp_path)

    dataset = builder.build()

    assert len(dataset) == 12
    assert (dataset["event_type"] == "shot").sum() == 4
    assert (dataset["event_type"] == "hit").sum() == 4
    assert (dataset["event_type"] == "kill").sum() == 4

    assert not dataset["weapon"].str.contains("knife", case=False).any()
    assert "weapon_flashbang" not in dataset["weapon"].values

    self_hits = dataset[
        (dataset["event_type"] == "hit")
        & (dataset["steamid"] == dataset["victim_steamid"])
    ]

    assert self_hits.empty


def test_player_level_samples(monkeypatch, tmp_path):
    monkeypatch.setattr("cs2guard_demo.dataset.builder.DemoParser", FakeDemoParser)
    create_fake_demos(tmp_path)

    builder = DatasetBuilder()
    builder.process_directory(tmp_path)

    player_dataset = builder.build_player_samples()

    assert len(player_dataset) == 4
    assert player_dataset[["match_id", "steamid"]].duplicated().sum() == 0

    for match_id in ["match_a", "match_b"]:
        match_players = player_dataset[player_dataset["match_id"] == match_id]

        assert len(match_players) == 2
        assert set(match_players["steamid"]) == {1, 2}

        assert (match_players["shots"] == 1).all()
        assert (match_players["hits"] == 1).all()
        assert (match_players["kills"] == 1).all()


def test_temporal_windows(monkeypatch, tmp_path):
    monkeypatch.setattr("cs2guard_demo.dataset.builder.DemoParser", FakeDemoParser)
    create_fake_demos(tmp_path)

    builder = DatasetBuilder()
    temporal_windows = builder.build_temporal_windows(tmp_path, window_size=32)

    assert temporal_windows["window_id"].nunique() == 4
    assert len(temporal_windows) == 128

    window_sizes = temporal_windows.groupby("window_id").size()

    assert (window_sizes == 32).all()
    assert temporal_windows["window_offset"].min() == 0
    assert temporal_windows["window_offset"].max() == 31


def test_aim_features(monkeypatch, tmp_path):
    monkeypatch.setattr("cs2guard_demo.dataset.builder.DemoParser", FakeDemoParser)
    create_fake_demos(tmp_path)

    builder = DatasetBuilder()
    temporal_windows = builder.build_temporal_windows(tmp_path, window_size=32)
    aim_features = builder.build_aim_features(temporal_windows, tick_rate=64.0)

    assert len(aim_features) == 4
    assert aim_features["window_id"].nunique() == 4
    assert aim_features["match_id"].nunique() == 2
    assert aim_features["steamid"].nunique() == 2

    feature_columns = [
        "mean_angular_speed",
        "max_angular_speed",
        "std_angular_speed",
        "mean_angular_acceleration",
        "max_angular_acceleration",
        "std_angular_acceleration",
    ]

    for column in feature_columns:
        assert aim_features[column].notna().all()
        assert aim_features[column].map(math.isfinite).all()


def test_invalid_data_helpers():
    assert safe_int(None) is None
    assert safe_int(float("nan")) is None
    assert safe_int(float("inf")) is None
    assert safe_int("invalid") is None
    assert safe_int("42") == 42

    assert safe_float(None) is None
    assert safe_float(float("nan")) is None
    assert safe_float(float("inf")) is None
    assert safe_float("invalid") is None
    assert safe_float("12.5") == 12.5

    assert not is_valid_player(None, "Player")
    assert not is_valid_player(0, "Player")
    assert not is_valid_player(-1, "Player")
    assert not is_valid_player(1, None)
    assert not is_valid_player(1, "")
    assert not is_valid_player(1, "   ")
    assert is_valid_player(1, "Player")

    assert is_ignored_weapon(None)
    assert is_ignored_weapon(float("nan"))
    assert is_ignored_weapon("")
    assert is_ignored_weapon("weapon_flashbang")
    assert is_ignored_weapon("weapon_knife")
    assert not is_ignored_weapon("weapon_ak47")

def test_fit_normalization_stats():
    dataset = pd.DataFrame(
        {
            "mean_angular_speed": [10.0, 20.0, 30.0],
            "max_angular_speed": [20.0, 40.0, 60.0],
            "std_angular_speed": [1.0, 2.0, 3.0],
            "mean_angular_acceleration": [100.0, 200.0, 300.0],
            "max_angular_acceleration": [200.0, 400.0, 600.0],
            "std_angular_acceleration": [10.0, 20.0, 30.0],
        }
    )

    stats = fit_normalization_stats(dataset, AIM_FEATURE_COLUMNS)

    assert set(stats) == set(AIM_FEATURE_COLUMNS)

    for column in AIM_FEATURE_COLUMNS:
        assert math.isfinite(stats[column]["mean"])
        assert math.isfinite(stats[column]["std"])
        assert stats[column]["std"] > 0.0


def test_normalize_features():
    dataset = pd.DataFrame(
        {
            "window_id": ["a", "b", "c"],
            "mean_angular_speed": [10.0, 20.0, 30.0],
            "max_angular_speed": [20.0, 40.0, 60.0],
            "std_angular_speed": [1.0, 2.0, 3.0],
            "mean_angular_acceleration": [100.0, 200.0, 300.0],
            "max_angular_acceleration": [200.0, 400.0, 600.0],
            "std_angular_acceleration": [10.0, 20.0, 30.0],
        }
    )

    stats = fit_normalization_stats(dataset, AIM_FEATURE_COLUMNS)
    normalized = normalize_features(dataset, stats)

    assert normalized["window_id"].tolist() == dataset["window_id"].tolist()

    for column in AIM_FEATURE_COLUMNS:
        assert math.isclose(normalized[column].mean(), 0.0, abs_tol=1e-12)
        assert math.isclose(normalized[column].std(ddof=0), 1.0, abs_tol=1e-12)


def test_normalization_handles_zero_variance():
    dataset = pd.DataFrame({"feature": [5.0, 5.0, 5.0]})

    stats = fit_normalization_stats(dataset, ["feature"])
    normalized = normalize_features(dataset, stats)

    assert stats["feature"]["std"] == 0.0
    assert (normalized["feature"] == 0.0).all()


def test_normalization_rejects_invalid_values():
    dataset = pd.DataFrame({"feature": [1.0, float("nan"), 3.0]})

    try:
        fit_normalization_stats(dataset, ["feature"])
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid normalization data to raise ValueError")

def test_apply_match_labels():
    dataset = pd.DataFrame(
        {
            "match_id": ["match_a", "match_a", "match_b"],
            "steamid": [1, 2, 3],
        }
    )

    labels = pd.DataFrame(
        {
            "match_id": ["match_a", "match_b"],
            "steamid": [pd.NA, pd.NA],
            "label": ["legitimate", "suspicious"],
        }
    )

    labeled = apply_labels(dataset, labels)

    assert labeled["label"].tolist() == [
        "legitimate",
        "legitimate",
        "suspicious",
    ]


def test_player_label_overrides_match_label():
    dataset = pd.DataFrame(
        {
            "match_id": ["match_a", "match_a"],
            "steamid": [1, 2],
        }
    )

    labels = pd.DataFrame(
        {
            "match_id": ["match_a", "match_a"],
            "steamid": [pd.NA, 2],
            "label": ["legitimate", "suspicious"],
        }
    )

    labeled = apply_labels(dataset, labels)

    assert labeled.loc[labeled["steamid"] == 1, "label"].iloc[0] == "legitimate"
    assert labeled.loc[labeled["steamid"] == 2, "label"].iloc[0] == "suspicious"


def test_unlabeled_samples_remain_unlabeled():
    dataset = pd.DataFrame(
        {
            "match_id": ["match_a", "match_b"],
            "steamid": [1, 2],
        }
    )

    labels = pd.DataFrame(
        {
            "match_id": ["match_a"],
            "steamid": [pd.NA],
            "label": ["legitimate"],
        }
    )

    labeled = apply_labels(dataset, labels)

    assert labeled.loc[0, "label"] == "legitimate"
    assert pd.isna(labeled.loc[1, "label"])


def test_invalid_label_is_rejected():
    labels = pd.DataFrame(
        {
            "match_id": ["match_a"],
            "steamid": [pd.NA],
            "label": ["cheater"],
        }
    )

    try:
        validate_labels(labels)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid label to raise ValueError")


def test_duplicate_player_labels_are_rejected():
    labels = pd.DataFrame(
        {
            "match_id": ["match_a", "match_a"],
            "steamid": [1, 1],
            "label": ["legitimate", "suspicious"],
        }
    )

    try:
        validate_labels(labels)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected duplicate player labels to raise ValueError")

def test_leakage_groups_connect_shared_players():
    dataset = pd.DataFrame(
        {
            "match_id": ["match_a", "match_a", "match_b", "match_b", "match_c"],
            "steamid": [1, 2, 2, 3, 4],
        }
    )

    groups = build_leakage_groups(dataset)

    match_a_group = groups[dataset["match_id"] == "match_a"].iloc[0]
    match_b_group = groups[dataset["match_id"] == "match_b"].iloc[0]
    match_c_group = groups[dataset["match_id"] == "match_c"].iloc[0]

    assert match_a_group == match_b_group
    assert match_a_group != match_c_group


def test_create_dataset_splits():
    rows = []

    for match_index in range(10):
        match_id = f"match_{match_index}"
        steamid = 1000 + match_index

        for sample_index in range(10):
            rows.append(
                {
                    "match_id": match_id,
                    "steamid": steamid,
                    "sample": sample_index,
                }
            )

    dataset = pd.DataFrame(rows)

    split_dataset = create_dataset_splits(
        dataset,
        train_ratio=0.7,
        validation_ratio=0.15,
        test_ratio=0.15,
        random_state=42,
    )

    assert "split" in split_dataset.columns
    assert set(split_dataset["split"]) == {"train", "validation", "test"}

    validate_no_data_leakage(split_dataset)


def test_match_never_crosses_splits():
    rows = []

    for match_index in range(6):
        for sample_index in range(5):
            rows.append(
                {
                    "match_id": f"match_{match_index}",
                    "steamid": 1000 + match_index,
                    "sample": sample_index,
                }
            )

    dataset = pd.DataFrame(rows)
    split_dataset = create_dataset_splits(dataset)

    split_counts = split_dataset.groupby("match_id")["split"].nunique()

    assert (split_counts == 1).all()


def test_player_never_crosses_splits():
    dataset = pd.DataFrame(
        {
            "match_id": [
                "match_a",
                "match_a",
                "match_b",
                "match_b",
                "match_c",
                "match_d",
                "match_e",
            ],
            "steamid": [
                1,
                2,
                2,
                3,
                4,
                5,
                6,
            ],
        }
    )

    split_dataset = create_dataset_splits(dataset)

    validate_no_data_leakage(split_dataset)

    player_split_counts = split_dataset.groupby("steamid")["split"].nunique()

    assert (player_split_counts == 1).all()


def test_split_is_reproducible():
    dataset = pd.DataFrame(
        {
            "match_id": [f"match_{index}" for index in range(20)],
            "steamid": [1000 + index for index in range(20)],
        }
    )

    first = create_dataset_splits(dataset, random_state=42)
    second = create_dataset_splits(dataset, random_state=42)

    assert first["split"].tolist() == second["split"].tolist()


def test_invalid_split_ratios_are_rejected():
    dataset = pd.DataFrame(
        {
            "match_id": ["match_a"],
            "steamid": [1],
        }
    )

    try:
        create_dataset_splits(dataset, train_ratio=0.8, validation_ratio=0.2, test_ratio=0.2)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid split ratios to raise ValueError")


def test_leakage_validation_detects_match_leakage():
    dataset = pd.DataFrame(
        {
            "match_id": ["match_a", "match_a"],
            "steamid": [1, 2],
            "split": ["train", "test"],
        }
    )

    try:
        validate_no_data_leakage(dataset)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected match leakage to raise ValueError")


def test_leakage_validation_detects_player_leakage():
    dataset = pd.DataFrame(
        {
            "match_id": ["match_a", "match_b"],
            "steamid": [1, 1],
            "split": ["train", "validation"],
        }
    )

    try:
        validate_no_data_leakage(dataset)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected player leakage to raise ValueError")

def test_generate_dataset_statistics():
    event_dataset = pd.DataFrame(
        {
            "match_id": ["match_a", "match_a", "match_b"],
            "steamid": [1, 2, 3],
            "event_type": ["shot", "hit", "kill"],
        }
    )

    player_dataset = pd.DataFrame(
        {
            "match_id": ["match_a", "match_a", "match_b"],
            "steamid": [1, 2, 3],
        }
    )

    temporal_windows = pd.DataFrame(
        {
            "window_id": ["window_a", "window_a", "window_b", "window_b"],
            "match_id": ["match_a", "match_a", "match_b", "match_b"],
        }
    )

    aim_features = pd.DataFrame(
        {
            "window_id": ["window_a", "window_b"],
            "match_id": ["match_a", "match_b"],
            "steamid": [1, 3],
            "mean_angular_speed": [10.0, 20.0],
            "max_angular_speed": [20.0, 40.0],
            "std_angular_speed": [2.0, 4.0],
            "mean_angular_acceleration": [100.0, 200.0],
            "max_angular_acceleration": [200.0, 400.0],
            "std_angular_acceleration": [20.0, 40.0],
        }
    )

    stats = generate_dataset_statistics(event_dataset, player_dataset, temporal_windows, aim_features)

    assert stats["events"]["samples"] == 3
    assert stats["events"]["matches"] == 2
    assert stats["events"]["players"] == 3
    assert stats["events"]["event_types"] == {"shot": 1, "hit": 1, "kill": 1}

    assert stats["players"]["samples"] == 3
    assert stats["players"]["unique_players"] == 3

    assert stats["temporal_windows"]["windows"] == 2
    assert stats["temporal_windows"]["rows"] == 4

    assert stats["aim_features"]["samples"] == 2
    assert stats["aim_features"]["matches"] == 2
    assert stats["aim_features"]["players"] == 2

    assert stats["aim_features"]["numerical"]["mean_angular_speed"]["mean"] == 15.0
    assert stats["aim_features"]["numerical"]["mean_angular_speed"]["min"] == 10.0
    assert stats["aim_features"]["numerical"]["mean_angular_speed"]["max"] == 20.0


def test_statistics_include_labels_and_splits():
    empty = pd.DataFrame()

    aim_features = pd.DataFrame(
        {
            "window_id": ["a", "b", "c"],
            "match_id": ["m1", "m2", "m3"],
            "steamid": [1, 2, 3],
            "label": ["legitimate", "legitimate", "suspicious"],
            "split": ["train", "validation", "test"],
        }
    )

    stats = generate_dataset_statistics(empty, empty, empty, aim_features)

    assert stats["aim_features"]["labels"] == {"legitimate": 2, "suspicious": 1}
    assert stats["aim_features"]["splits"] == {"train": 1, "validation": 1, "test": 1}