"""Synthetic checks for match-scoped evaluation and clustered uncertainty."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

from cs2guard_demo.cs2cd_validation import classification_summary, cluster_bootstrap, rank_players
from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS


def players_fixture():
    return pd.DataFrame([
        {"match_id": "a", "player_id": "Player_2", "label": "suspicious", "score": .5},
        {"match_id": "a", "player_id": "Player_1", "label": "legitimate", "score": .5},
        {"match_id": "b", "player_id": "Player_1", "label": "suspicious", "score": .9},
        {"match_id": "b", "player_id": "Player_2", "label": "legitimate", "score": .2},
        {"match_id": "c", "player_id": "Player_1", "label": "legitimate", "score": .8},
    ])


def test_ranking_ties_match_scoped_ids_and_positive_hit_denominator():
    players = players_fixture()
    ranked = rank_players(players.sample(frac=1, random_state=7))
    assert ranked.player_id.tolist() == ["Player_1", "Player_2", "Player_1", "Player_2", "Player_1"]
    assert ranked["rank"].tolist() == [1, 2, 1, 2, 1]
    assert len(ranked) == 5  # Repeated anonymous names remain distinct player-matches.
    summary = classification_summary(players)
    assert summary["counts"] == {"matches": 3, "player_matches": 5, "legitimate_player_matches": 3,
                                 "suspicious_player_matches": 2, "positive_matches": 2, "positive_prevalence": .4}
    assert summary["hit_at_1"] == .5 and summary["hit_at_3"] == 1
    half = next(row for row in summary["thresholds"] if row["threshold"] == .5)
    assert {key: half[key] for key in ["tn", "fp", "fn", "tp"]} == {"tn": 1, "fp": 2, "fn": 0, "tp": 2}
    assert half["precision"] == .5 and half["recall"] == 1
    assert half["false_positive_rate"] == pytest.approx(2 / 3)
    assert summary["discrimination"]["pr_auc"] == average_precision_score([0, 1, 1, 0, 0], [.5, .5, .9, .2, .8])
    assert players.columns.tolist() == ["match_id", "player_id", "label", "score"]


def test_match_bootstrap_matches_explicit_concatenation_and_is_deterministic():
    players = players_fixture()
    draws, seed = 100, 12
    bootstrap = cluster_bootstrap(players, seed=seed, draws=draws)
    assert bootstrap == cluster_bootstrap(players.sample(frac=1, random_state=2), seed=seed, draws=draws)
    samples = np.random.default_rng(seed).integers(0, 3, size=(draws, 3))
    matches = sorted(players.match_id.unique())
    measured = {name: [] for name in ["roc_auc", "pr_auc", "precision", "recall", "f1", "false_positive_rate", "hit_at_1", "hit_at_3"]}
    excluded = 0
    for sample in samples:
        pieces = []
        for index, match_index in enumerate(sample):
            piece = players[players.match_id.eq(matches[match_index])].copy()
            piece["match_id"] = f"draw_{index}"
            pieces.append(piece)
        repeated = pd.concat(pieces, ignore_index=True)
        targets = repeated.label.eq("suspicious").astype(int)
        if targets.nunique() != 2:
            excluded += 1
        summary = classification_summary(repeated)
        for name in ["roc_auc", "pr_auc"]:
            if summary["discrimination"][name] is not None:
                measured[name].append(summary["discrimination"][name])
        half = next(row for row in summary["thresholds"] if row["threshold"] == .5)
        for name in ["precision", "recall", "f1", "false_positive_rate"]:
            if half[name] is not None:
                measured[name].append(half[name])
        for name in ["hit_at_1", "hit_at_3"]:
            if summary[name] is not None:
                measured[name].append(summary[name])
    assert excluded > 0
    assert bootstrap["discrimination_valid_draws"] == draws - excluded
    assert bootstrap["positive_draws"] == draws - excluded
    assert bootstrap["negative_draws"] == draws
    half = next(row for row in bootstrap["thresholds"] if row["threshold"] == .5)
    for name, values in measured.items():
        interval = bootstrap["discrimination"][name] if name in {"roc_auc", "pr_auc"} else (half[name] if name in half else bootstrap[name])
        assert interval["interval"] == pytest.approx(np.quantile(values, [.025, .975]))
        assert interval["valid_draws"] == len(values)


def test_threshold_zero_predictions_and_single_match_intervals():
    players = players_fixture()
    players["score"] = .2
    summary = classification_summary(players)
    at_half = next(row for row in summary["thresholds"] if row["threshold"] == .5)
    assert at_half["precision"] == at_half["recall"] == at_half["f1"] == at_half["false_positive_rate"] == 0
    one_match = cluster_bootstrap(players[players.match_id.eq("a")], draws=100)
    assert one_match["discrimination"]["roc_auc"]["interval"] is None
    assert one_match["hit_at_1"]["interval"] is None
    assert all(row["precision"]["interval"] is None for row in one_match["thresholds"])


@pytest.mark.parametrize("arguments", [{"draws": 99}, {"draws": 100.5}, {"seed": -1}, {"seed": .5}])
def test_invalid_bootstrap_settings(arguments):
    with pytest.raises(ValueError, match="bootstrap draws"):
        cluster_bootstrap(players_fixture(), **arguments)


def test_invalid_populations_are_rejected():
    players = players_fixture()
    with pytest.raises(ValueError, match="Duplicate"):
        rank_players(pd.concat([players, players.iloc[:1]], ignore_index=True))
    for bad in [np.nan, np.inf, -.1, 1.1]:
        changed = players.copy()
        changed.loc[0, "score"] = bad
        with pytest.raises(ValueError, match="scores"):
            rank_players(changed)


@pytest.mark.parametrize("label", ["legitimate", "suspicious"])
def test_single_class_populations_keep_defined_metrics(label):
    players = players_fixture()
    players["label"] = label
    summary = classification_summary(players)
    bootstrap = cluster_bootstrap(players, draws=100)
    assert summary["discrimination"] == {"roc_auc": None, "pr_auc": None}
    assert bootstrap["discrimination_valid_draws"] == 0
    assert bootstrap["discrimination"]["roc_auc"]["interval"] is None
    half = next(row for row in summary["thresholds"] if row["threshold"] == .5)
    half_ci = next(row for row in bootstrap["thresholds"] if row["threshold"] == .5)
    assert half_ci["precision"]["valid_draws"] == 100
    if label == "legitimate":
        assert half["recall"] is half["f1"] is summary["hit_at_1"] is summary["hit_at_3"] is None
        assert half["precision"] == 0 and half["false_positive_rate"] == .8
        assert half_ci["false_positive_rate"]["valid_draws"] == 100
        assert half_ci["recall"]["interval"] is bootstrap["hit_at_1"]["interval"] is None
    else:
        assert half["false_positive_rate"] is None
        assert half["recall"] == .8 and half["precision"] == 1
        assert summary["hit_at_1"] == summary["hit_at_3"] == 1
        assert half_ci["recall"]["valid_draws"] == 100
        assert half_ci["false_positive_rate"]["interval"] is None


@pytest.fixture
def evaluation_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_cs2cd.py"
    spec = importlib.util.spec_from_file_location("evaluate_cs2cd_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FrozenScores:
    classes_ = np.array([1, 0])  # The positive column must be found by class value.

    def predict_proba(self, features):
        scores = features[FEATURE_COLUMNS[0]].to_numpy() / 1000
        return np.column_stack([scores, 1 - scores])


def test_driver_inference_is_positional_and_preserves_player_means(evaluation_script):
    rows = []
    for index, (match, pid, label, score) in enumerate([
        ("a", "Player_1", "legitimate", .2), ("b", "Player_1", "suspicious", .8),
        ("a", "Player_1", "legitimate", .4), ("a", "Player_2", "suspicious", .3),
    ]):
        rows.append({"source": "cs2cd", "match_id": match, "player_id": f"cs2cd:{match}:{pid}",
                     "source_player_id": pid, "identity_scope": "match", "label": label,
                     "window_id": f"window_{index}", "shot_tick": index,
                     **{feature: score * 1000 for feature in FEATURE_COLUMNS}})
    features = pd.DataFrame(rows, index=[90, 3, 21, 8])
    players, windows, delta = evaluation_script.score_features(features, FrozenScores(), FrozenScores())
    assert windows.index.tolist() == [90, 3, 21, 8]
    assert windows.score.tolist() == pytest.approx([.2, .8, .4, .3])
    by_player = players.set_index(["match_id", "player_id"])
    assert by_player.loc[("a", "cs2cd:a:Player_1"), "score"] == pytest.approx(.3)
    assert by_player.loc[("a", "cs2cd:a:Player_1"), "window_count"] == 2
    assert delta == 0
    changed = features.copy()
    changed.loc[90, "player_id"] = "cs2cd:other:Player_1"
    with pytest.raises(ValueError, match="identity mismatch"):
        evaluation_script.score_features(changed, FrozenScores(), FrozenScores())
    with pytest.raises(ValueError, match="Duplicate windows"):
        evaluation_script.score_features(pd.concat([features, features.iloc[:1]]), FrozenScores(), FrozenScores())
    class InvalidRepeat(FrozenScores):
        def predict_proba(self, features):
            return np.full((len(features), 2), np.nan)
    with pytest.raises(ValueError, match="Invalid repeated inference"):
        evaluation_script.score_features(features, FrozenScores(), InvalidRepeat())


def test_driver_raw_partition_cache_and_negative_population(tmp_path, monkeypatch, evaluation_script):
    raw = tmp_path / "raw" / "cs2cd"
    raw.mkdir(parents=True)
    match_ids = []
    for index, name in enumerate(["train", "test", "unused"]):
        path = raw / f"{name}.json"
        events = {"weapon_fire": [{"tick": 131, "user_steamid": "Player_1", "weapon": "ak47"},
                                   {"tick": 231, "user_steamid": "Player_2", "weapon": "ak47"}],
                  "player_hurt": [{"tick": 131, "attacker_steamid": "Player_1", "user_steamid": "Player_3"}],
                  "cheaters": [{"steamid": "Player_2"}] if name != "unused" else [],
                  "CSstats_info": [{"map": f"de_map_{index}"}]}
        path.write_text(json.dumps(events), encoding="utf-8")
        ticks = pd.DataFrame([{"tick": tick, "steamid": f"Player_{player}", "X": 0., "Y": 0., "Z": 0.,
                               "yaw": (tick - start) * player, "pitch": 0.}
                              for player, start in [(1, 100), (2, 200)] for tick in range(start, start + 32)])
        invalid = ticks.iloc[:1].copy()
        invalid["yaw"] = np.nan
        pd.concat([ticks, invalid], ignore_index=True).to_parquet(path.with_suffix(".parquet"), index=False)
        match_ids.append(evaluation_script.CS2CDAdapter(path, path.with_suffix(".parquet")).match_id)
    train = pd.DataFrame({"match_id": [match_ids[0]]})
    test = pd.DataFrame({"match_id": [match_ids[1]]})
    inventory, roster = evaluation_script.audit_sources(tmp_path / "raw", train, test)
    partitions = {row["match_id"]: row["partition"] for row in inventory}
    assert partitions == {match_ids[0]: "training", match_ids[1]: "historical_test", match_ids[2]: "unused_negative"}
    with pytest.raises(ValueError, match="overlap"):
        evaluation_script.audit_sources(tmp_path / "raw", train, train)
    item = next(row for row in inventory if row["partition"] == "unused_negative")
    cache = tmp_path / "cache"
    match, features, receipt = evaluation_script.extract_match(item, cache)
    assert match == match_ids[2] and len(features) == receipt["windows"] == 2
    assert receipt["raw_tick_rows"] == 65 and receipt["retained_tick_rows"] == 64
    assert receipt["discarded_invalid_tick_rows"] == 1
    assert features.label.eq("legitimate").all()
    monkeypatch.setattr(evaluation_script.DatasetBuilder, "build_aim_features", lambda *a, **k: pytest.fail("Verified cache must be reused"))
    cached_match, cached, cached_receipt = evaluation_script.extract_match(item, cache)
    pd.testing.assert_frame_equal(cached, features)
    assert cached_match == match and cached_receipt == receipt
    players, _, _ = evaluation_script.score_features(features, FrozenScores(), FrozenScores())
    output = tmp_path / "output"
    output.mkdir()
    result = evaluation_script.save_population("negative", players, output, roster, seed=42, draws=100)
    assert result["metrics"]["discrimination"] == {"roc_auc": None, "pr_auc": None}
    assert result["roster_player_matches"] == 3 and result["unscored_player_matches"] == 1
    assert json.loads((output / "negative_metrics.json").read_text(encoding="utf-8")) == result
    csv = cache / match / "features.csv"
    original_csv = csv.read_bytes()
    csv.write_bytes(original_csv + b"\n")
    with pytest.raises(ValueError, match="cache integrity failure"):
        evaluation_script.extract_match(item, cache)
    csv.write_bytes(original_csv)
    telemetry = Path(item["parquet_path"])
    telemetry.write_bytes(telemetry.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="cache integrity failure"):
        evaluation_script.extract_match(item, cache)


def test_driver_match_without_shots_retains_empty_cache_and_roster(tmp_path, monkeypatch, evaluation_script):
    raw = tmp_path / "cs2cd"
    raw.mkdir()
    path = raw / "no_shots.json"
    events = {"weapon_fire": [], "cheaters": [],
              "player_hurt": [{"tick": 131, "attacker_steamid": "Player_1", "user_steamid": "Player_2"}]}
    path.write_text(json.dumps(events), encoding="utf-8")
    pd.DataFrame([{"tick": tick, "steamid": "Player_1", "X": 0., "Y": 0., "Z": 0.,
                   "yaw": float(tick), "pitch": 0.} for tick in range(100, 132)]).to_parquet(path.with_suffix(".parquet"), index=False)
    empty_split = pd.DataFrame(columns=["match_id"])
    inventory, roster = evaluation_script.audit_sources(raw, empty_split, empty_split)
    item = inventory[0]
    match, features, receipt = evaluation_script.extract_match(item, tmp_path / "cache")
    assert features.empty and features.columns.tolist() == evaluation_script.AIM_FEATURE_COLUMNS
    assert receipt["windows"] == receipt["window_tick_rows"] == receipt["unique_shot_events"] == 0
    assert receipt["raw_tick_rows"] == receipt["retained_tick_rows"] == 32
    assert receipt["canonical_events"] == 1
    monkeypatch.setattr(evaluation_script.DatasetBuilder, "build_aim_features", lambda *a, **k: pytest.fail("Empty verified cache must be reused"))
    cached_match, cached, cached_receipt = evaluation_script.extract_match(item, tmp_path / "cache")
    assert cached_match == match and cached_receipt == receipt
    pd.testing.assert_frame_equal(cached, features)
    scored = pd.DataFrame([{"match_id": "scored", "player_id": "cs2cd:scored:Player_1", "label": "legitimate", "score": .25}])
    scored_roster = pd.DataFrame([{"source": "cs2cd", "match_id": "scored", "player_id": "cs2cd:scored:Player_1",
                                   "source_player_id": "Player_1", "identity_scope": "match", "label": "legitimate"}])
    output = tmp_path / "output"
    output.mkdir()
    result = evaluation_script.save_population("with_empty", scored, output, pd.concat([roster, scored_roster]),
                                                seed=42, draws=100, match_ids=["scored", match])
    assert result["processed_matches"] == 2 and result["matches_without_scores"] == [match]
    assert result["roster_player_matches"] == 3 and result["unscored_player_matches"] == 2
    assert result["metrics"]["counts"]["matches"] == result["metrics"]["counts"]["player_matches"] == 1
    saved_roster = pd.read_csv(output / "with_empty_roster.csv")
    assert saved_roster.match_id.eq(match).sum() == 2
    assert saved_roster.loc[saved_roster.match_id.eq(match), "score"].isna().all()
