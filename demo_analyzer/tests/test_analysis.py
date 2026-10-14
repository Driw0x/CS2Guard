import json
import io
from pathlib import Path
import subprocess
import sys

import joblib
import matplotlib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier

matplotlib.use("Agg")
from matplotlib.image import imread

import cs2guard_demo.parser.demo_parser as parser_module
from cs2guard_demo.analysis import analyze_demo, load_analysis_model, tree_probability_contributions
from cs2guard_demo.cli import main
from cs2guard_demo.detection import FEATURE_COLUMNS
from cs2guard_demo.supervised import LABEL_TO_TARGET, save_model_bundle


class FakeDemoparser:
    """Only replace the external parser; keep M1, M2, M3 and M5 integration real."""

    def __init__(self):
        rows = []
        for steamid, name, first_step, second_step, x in (
            (1, "Alpha", 1, 2, 0.0),
            (2, "Bravo", 2, 2, 100.0),
        ):
            for start, step in ((100, first_step), (200, second_step)):
                for offset in range(32):
                    rows.append({"tick": start + offset, "steamid": steamid, "name": name,
                                 "team_name": "CT", "X": x, "Y": 0.0, "Z": 0.0,
                                 "yaw": float(step * offset), "pitch": 0.0})
        for tick in range(100, 110):
            rows.append({"tick": tick, "steamid": 3, "name": "Partial", "team_name": "T",
                         "X": 200.0, "Y": 0.0, "Z": 0.0, "yaw": 0.0, "pitch": 0.0})
        self.ticks = pd.DataFrame(rows)
        self.roster = pd.DataFrame({"tick": [100, 100, 100, 99], "steamid": [1, 2, 3, 4],
                                    "name": ["Alpha", "Bravo", "Partial", "Roster"],
                                    "team_name": ["CT", "CT", "T", "T"]})
        self.events = {
            "begin_new_match": pd.DataFrame({"tick": [100]}),
            "round_start": pd.DataFrame({"tick": [100, 200], "round": [1, 2]}),
            "round_end": pd.DataFrame({"tick": [160, 260], "round": [1, 2],
                                        "winner": ["CT", "T"], "reason": ["t_killed", "ct_killed"]}),
            "weapon_fire": pd.DataFrame([
                {"tick": tick, "user_steamid": player, "user_name": name, "weapon": "ak47"}
                for player, name, ticks in ((1, "Alpha", (131, 231)),
                                            (2, "Bravo", (131, 231)), (3, "Partial", (109,)))
                for tick in ticks
            ]),
            "player_hurt": pd.DataFrame([
                {"tick": tick, "attacker_steamid": attacker, "attacker_name": name,
                 "user_steamid": victim, "user_name": victim_name, "weapon": "ak47",
                 "dmg_health": 30, "dmg_armor": 5, "health": 70, "armor": 95, "hitgroup": "chest"}
                for tick, attacker, name, victim, victim_name in (
                    (132, 1, "Alpha", 2, "Bravo"),
                    (235, 1, "Alpha", 5, "VictimOnly"),
                    (131, 2, "Bravo", 5, "VictimOnly"),
                )
            ]),
            "player_death": pd.DataFrame([
                {"tick": tick, "attacker_steamid": attacker, "attacker_name": name,
                 "user_steamid": victim, "user_name": victim_name, "weapon": "ak47",
                 "headshot": True, "distance": 100.0, "hitgroup": "head", "noscope": False,
                 "penetrated": 0, "thrusmoke": False, "attackerblind": False, "attackerinair": False}
                for tick, attacker, name, victim, victim_name in (
                    (133, 1, "Alpha", 2, "Bravo"), (233, 2, "Bravo", 5, "VictimOnly"),
                )
            ]),
        }

    def parse_ticks(self, fields):
        return (self.roster if fields == ["team_name"] else self.ticks).copy()

    def parse_event(self, name):
        return self.events[name].copy()

    def parse_header(self):
        return {"map_name": "de_mirage", "patch_version": 12345, "demo_version_name": "valve_demo_2"}


@pytest.fixture
def analysis_inputs(tmp_path, monkeypatch):
    backend = FakeDemoparser()
    monkeypatch.setattr(parser_module, "Demoparser2", lambda path: backend)
    demo_path = tmp_path / "match.dem"
    demo_path.write_bytes(b"controlled demo fixture")
    training = pd.DataFrame(0.0, index=range(4), columns=FEATURE_COLUMNS)
    training["mean_angular_speed"] = [0.0, 64.0, 128.0, 256.0]
    model = DecisionTreeClassifier(random_state=42).fit(training, [0, 0, 1, 1])
    metadata = {"model_name": "controlled_tree", "version": "v1", "features": FEATURE_COLUMNS,
                "label_mapping": LABEL_TO_TARGET, "decision_threshold": None}
    model_path, _ = save_model_bundle(model, metadata, tmp_path / "models", "controlled_tree", "v1")
    return demo_path, model_path, backend


def test_analyze_demo_end_to_end(analysis_inputs, tmp_path, monkeypatch):
    demo_path, model_path, _ = analysis_inputs
    monkeypatch.setattr(DecisionTreeClassifier, "fit", lambda *args, **kwargs: pytest.fail("Analysis must not retrain"))
    output = tmp_path / "analysis"
    report = analyze_demo(demo_path, model_path, output)

    assert report["match"]["match_id"] == "match"
    assert report["match"]["map_name"] == "de_mirage"
    assert report["summary"] == {"status": "partial", "player_count": 5, "scored_player_count": 2,
                                 "tick_count": 138, "event_count": 10, "window_count": 4, "round_count": 2,
                                 "unscored_shot_count": 1, "missing_round_window_count": 0,
                                 "cross_round_window_count": 0}
    players = report["players"]
    assert [player["player_id"] for player in players] == ["demo:2", "demo:1", "demo:3", "demo:4", "demo:5"]
    assert [player["rank"] for player in players] == [1, 2, None, None, None]
    assert [player["score"] for player in players] == [1.0, 0.5, None, None, None]
    assert [player["window_count"] for player in players] == [2, 2, 0, 0, 0]
    assert [player["unscored_shot_count"] for player in players] == [0, 0, 1, 0, 0]
    assert players[-1]["player_name"] == "VictimOnly"
    assert all(player["status"] == "insufficient_data" and player["reason"] for player in players[2:])
    assert players[1]["behavioral_scores"]["kind"] == "descriptive_indicators"
    assert players[1]["behavioral_scores"]["angular_speed"] == {"value": 96.0, "unit": "degrees/second"}
    assert players[1]["behavioral_scores"]["angular_acceleration"] == {"value": 0.0, "unit": "degrees/second^2"}
    assert all(player["behavioral_scores"]["reaction"]["value"] is None for player in players)
    assert report["model"]["features"] == FEATURE_COLUMNS
    assert report["model"]["score_kind"] == "uncalibrated_supervised_class1_probability"
    assert report["model"]["decision_threshold"] is None
    assert report["model"]["threshold_applied"] is False
    assert report["feature_importance"]["kind"] == "global_model_importance_not_local_attribution"
    assert report["feature_importance"]["values"]["mean_angular_speed"] == 1.0
    assert players[1]["model_contributions"]["baseline"] == 0.5
    assert players[1]["model_contributions"]["features"]["mean_angular_speed"] == 0.0
    assert players[0]["model_contributions"]["features"]["mean_angular_speed"] == 0.5
    for player in players:
        contribution = player["model_contributions"]
        if player["score"] is None:
            assert contribution is None
        else:
            assert contribution["method"] == "mean_tree_probability_path"
            assert contribution["baseline"] + sum(contribution["features"].values()) == pytest.approx(player["score"], rel=0, abs=1e-12)

    windows = report["windows"]
    assert len({window["window_id"] for window in windows}) == 4
    for window in windows:
        assert window["tick_count"] == 32
        assert window["start_tick"] == window["shot_tick"] - 31
        assert window["end_tick"] == window["shot_tick"]
        assert window["round_number"] == (1 if window["shot_tick"] == 131 else 2)
        assert not window["crosses_round_boundary"]
        assert list(window["features"]) == FEATURE_COLUMNS
        assert all(event["player_id"] == window["player_id"] for event in window["events"])
        assert all(abs(event["tick"] - window["shot_tick"]) <= 2 for event in window["events"])
        contribution = window["model_contributions"]
        assert contribution["method"] == "tree_probability_path"
        assert contribution["baseline"] == 0.5
        assert contribution["features"]["mean_angular_speed"] == window["score"] - 0.5
        assert all(contribution["features"][name] == 0.0 for name in FEATURE_COLUMNS[1:])
        assert contribution["score"] == window["score"]
        assert contribution["baseline"] + sum(contribution["features"].values()) == pytest.approx(window["score"], rel=0, abs=1e-12)
        assert "not causal" in contribution["interpretation"]
    alpha_first = next(window for window in windows if window["player_id"] == "demo:1" and window["shot_tick"] == 131)
    alpha_second = next(window for window in windows if window["player_id"] == "demo:1" and window["shot_tick"] == 231)
    assert [event["event_type"] for event in alpha_first["events"]] == ["shot", "hit", "kill"]
    assert [event["event_type"] for event in alpha_second["events"]] == ["shot"]
    assert alpha_first["visualization"]["reference"] == "observed_victim_position"
    assert alpha_first["visualization"]["target_id"] == "demo:2"
    assert alpha_first["visualization"]["tracking"]["mean_error_degrees"] == pytest.approx(15.5)
    assert alpha_second["visualization"]["reference"] == "shot_aim_direction"
    assert alpha_second["visualization"]["tracking"] is None
    assert "No hit or kill linked" in alpha_second["visualization"]["tracking_unavailable_reason"]
    assert [round_row["window_count"] for round_row in report["rounds"]] == [2, 2]
    assert [round_row["max_window_score"] for round_row in report["rounds"]] == [1.0, 1.0]
    assert [window["score"] for window in report["review_events"]] == [1.0, 1.0, 1.0, 0.0]
    assert any("not calibrated" in limit for limit in report["limitations"])
    assert any("not a local" in window["explanation"] for window in windows)

    assert json.loads((output / "report.json").read_text(encoding="utf-8")) == report
    markdown = (output / "report.md").read_text(encoding="utf-8")
    assert "not proof of cheating" in markdown
    assert "N/A" in markdown and "demo:5" in markdown
    assert "## Behavioral indicators" in markdown and "## Rounds ordered for inspection" in markdown
    assert "windows without completed round: 0; windows crossing round boundaries: 0" in markdown
    assert "Tracking unavailable: No hit or kill linked" in markdown
    assert "## Player model contributions" in markdown and "Signed path probability change" in markdown
    for window in report["review_events"]:
        image_path = output / window["visualization"]["path"]
        assert image_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        pixels = imread(image_path)
        assert pixels.shape[0] > 100 and pixels.shape[1] > 100 and pixels.std() > 0
        assert f"({image_path.name})" in markdown


def test_ranking_ties_and_reproducibility(analysis_inputs, tmp_path):
    demo_path, model_path, backend = analysis_inputs
    alpha = backend.ticks["steamid"].eq(1)
    backend.ticks.loc[alpha, "yaw"] = 2.0 * (backend.ticks.loc[alpha, "tick"] % 100)
    first = analyze_demo(demo_path, model_path, tmp_path / "first")
    backend.ticks = backend.ticks.iloc[::-1].reset_index(drop=True)
    backend.roster = backend.roster.iloc[::-1].reset_index(drop=True)
    second = analyze_demo(demo_path, model_path, tmp_path / "second")
    assert [player["player_id"] for player in first["players"][:2]] == ["demo:1", "demo:2"]
    assert [player["score"] for player in first["players"][:2]] == [1.0, 1.0]
    assert first == second
    assert (tmp_path / "first" / "report.json").read_bytes() == (tmp_path / "second" / "report.json").read_bytes()


@pytest.mark.parametrize("missing", ["shots", "ticks", "all"])
def test_insufficient_data_preserves_players(analysis_inputs, tmp_path, missing):
    demo_path, model_path, backend = analysis_inputs
    if missing in {"ticks", "all"}:
        backend.ticks = backend.ticks.iloc[:0]
    if missing in {"shots", "all"}:
        backend.events["weapon_fire"] = backend.events["weapon_fire"].iloc[:0]
    if missing == "all":
        backend.roster = backend.roster.iloc[:0]
        backend.events["player_hurt"] = backend.events["player_hurt"].iloc[:0]
        backend.events["player_death"] = backend.events["player_death"].iloc[:0]
        backend.events["round_start"] = backend.events["round_start"].iloc[:0]
        backend.events["round_end"] = backend.events["round_end"].iloc[:0]
    report = analyze_demo(demo_path, model_path, tmp_path / "insufficient")
    assert report["summary"]["status"] == "insufficient_data"
    assert report["summary"]["scored_player_count"] == report["summary"]["window_count"] == 0
    assert report["summary"]["player_count"] == (0 if missing == "all" else 5)
    assert report["windows"] == report["review_events"] == []
    assert all(player["score"] is None and player["rank"] is None for player in report["players"])
    assert all(player["status"] == "insufficient_data" for player in report["players"])
    assert json.loads((tmp_path / "insufficient" / "report.json").read_text(encoding="utf-8")) == report
    assert not list((tmp_path / "insufficient").glob("*.png"))


@pytest.mark.parametrize("round_data", ["complete", "partial"])
def test_single_player_and_review_limit(analysis_inputs, tmp_path, round_data):
    demo_path, model_path, backend = analysis_inputs
    backend.ticks = backend.ticks[backend.ticks["steamid"].eq(1)].copy()
    original = backend.ticks[backend.ticks["tick"].between(100, 131)].copy()
    extra = pd.concat([original.assign(tick=original["tick"] + offset) for offset in (32, 64)])
    backend.ticks = pd.concat([backend.ticks, extra], ignore_index=True)
    backend.roster = backend.roster[backend.roster["steamid"].eq(1)]
    shots = backend.events["weapon_fire"]
    shots = shots[shots["user_steamid"].eq(1)]
    extra_shots = pd.concat([shots.iloc[:1].assign(tick=tick) for tick in (163, 195)])
    backend.events["weapon_fire"] = pd.concat([shots, extra_shots], ignore_index=True)
    backend.events["player_hurt"] = backend.events["player_hurt"].iloc[:0]
    backend.events["player_death"] = backend.events["player_death"].iloc[:0]
    if round_data == "complete":
        backend.events["round_end"].loc[0, "tick"] = 199
    report = analyze_demo(demo_path, model_path, tmp_path / "single")
    assert report["summary"]["status"] == round_data
    assert report["summary"]["player_count"] == report["summary"]["scored_player_count"] == 1
    assert report["summary"]["window_count"] == 4
    assert report["players"][0]["score"] == 0.25
    assert len(report["review_events"]) == len(report["players"][0]["review_window_ids"]) == 3
    assert [window["shot_tick"] for window in report["review_events"]] == [231, 131, 163]
    assert report["summary"]["missing_round_window_count"] == (2 if round_data == "partial" else 0)
    assert report["summary"]["cross_round_window_count"] == (1 if round_data == "partial" else 0)
    if round_data == "partial":
        assert any(window["round_number"] is None for window in report["windows"])
        assert next(window for window in report["windows"] if window["shot_tick"] == 163)["crosses_round_boundary"]
        assert any("no completed round" in limit for limit in report["limitations"])
        assert any("cross round boundaries" in limit for limit in report["limitations"])


@pytest.mark.parametrize("key,value,message", [
    ("features", FEATURE_COLUMNS[::-1], "features"),
    ("label_mapping", {"legitimate": 1, "suspicious": 0}, "label mapping"),
    ("model_name", "", "model_name"),
    ("version", None, "version"),
    ("window_size", 16, "window_size"),
    ("tick_rate", 128.0, "tick_rate"),
])
def test_incompatible_model_metadata(analysis_inputs, key, value, message):
    _, model_path, _ = analysis_inputs
    path = model_path.with_suffix(".json")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata[key] = value
    path.write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_analysis_model(model_path)


@pytest.mark.parametrize("attribute,value,message", [
    ("classes_", np.array([0]), "classes"),
    ("classes_", np.array([0, 2]), "classes"),
    ("classes_", np.array(["legitimate", "suspicious"]), "classes"),
    ("n_features_in_", 5, "dimension"),
    ("feature_names_in_", np.array(FEATURE_COLUMNS[::-1]), "feature names"),
    ("predict_proba", None, "predict_proba"),
])
def test_incompatible_model_estimator(analysis_inputs, attribute, value, message):
    _, model_path, _ = analysis_inputs
    model = joblib.load(model_path)
    setattr(model, attribute, value)
    joblib.dump(model, model_path)
    with pytest.raises(ValueError, match=message):
        load_analysis_model(model_path)


@pytest.mark.parametrize("artifact,error", [
    ("model", FileNotFoundError), ("metadata", FileNotFoundError),
    ("corrupt_metadata", ValueError), ("corrupt_model", EOFError),
])
def test_unreadable_model_bundle(analysis_inputs, artifact, error):
    _, model_path, _ = analysis_inputs
    if artifact == "model":
        model_path.unlink()
    elif artifact == "metadata":
        model_path.with_suffix(".json").unlink()
    elif artifact == "corrupt_metadata":
        model_path.with_suffix(".json").write_text("[]", encoding="utf-8")
    else:
        model_path.write_bytes(b"")
    with pytest.raises(error):
        load_analysis_model(model_path)


@pytest.mark.parametrize("probabilities", [
    [np.nan, np.nan], [2.0, -1.0], [0.2, 0.2], [1.0],
])
def test_invalid_model_probabilities(analysis_inputs, tmp_path, monkeypatch, probabilities):
    demo_path, model_path, _ = analysis_inputs
    monkeypatch.setattr(DecisionTreeClassifier, "predict_proba", lambda self, data: np.tile(probabilities, (len(data), 1)))
    with pytest.raises(ValueError, match="probabilit"):
        analyze_demo(demo_path, model_path, tmp_path / "invalid_probabilities")
    assert not (tmp_path / "invalid_probabilities" / "report.json").exists()


def test_probability_uses_class_one_column(analysis_inputs, tmp_path, monkeypatch):
    demo_path, model_path, _ = analysis_inputs
    training = pd.DataFrame(0.0, index=range(2), columns=FEATURE_COLUMNS)
    model = LogisticRegression().fit(training, [0, 1])
    model.classes_ = np.array([1, 0])
    joblib.dump(model, model_path)
    monkeypatch.setattr(LogisticRegression, "predict_proba", lambda self, data: np.tile([0.8, 0.2], (len(data), 1)))
    report = analyze_demo(demo_path, model_path, tmp_path / "class_order")
    assert all(window["score"] == 0.8 for window in report["windows"])
    assert all(player["score"] == 0.8 for player in report["players"] if player["status"] == "scored")
    assert report["feature_importance"]["values"] is None
    assert tree_probability_contributions(model, training) is None
    assert all(window["model_contributions"] is None for window in report["windows"])
    assert all(player["model_contributions"] is None for player in report["players"])
    markdown = (tmp_path / "class_order" / "report.md").read_text(encoding="utf-8")
    assert "Local model contributions unavailable for this estimator family." in markdown


def test_tree_contributions_exact_split_and_float32_input(analysis_inputs):
    _, model_path, _ = analysis_inputs
    model, _ = load_analysis_model(model_path)
    features = pd.DataFrame(0.0, index=range(5), columns=FEATURE_COLUMNS)
    features["mean_angular_speed"] = [64.0, 96.0000001, 128.0, -1e30, 1e30]
    baseline, contributions = tree_probability_contributions(model, features)
    assert baseline == 0.5
    expected = np.zeros((5, 6))
    expected[:, 0] = [-0.5, -0.5, 0.5, -0.5, 0.5]
    np.testing.assert_array_equal(contributions, expected)
    np.testing.assert_array_equal(baseline + contributions.sum(axis=1), model.predict_proba(features)[:, 1])


def test_random_forest_contributions_reconstruct_persisted_probabilities(analysis_inputs):
    _, model_path, _ = analysis_inputs
    training = pd.DataFrame(0.0, index=range(4), columns=FEATURE_COLUMNS)
    training["mean_angular_speed"] = [0.0, 64.0, 128.0, 256.0]
    model = RandomForestClassifier(n_estimators=3, max_depth=3, max_features=None, random_state=42)
    model.fit(training, [0, 1, 0, 1], sample_weight=[1.0, 2.0, 3.0, 4.0])
    joblib.dump(model, model_path)
    loaded, _ = load_analysis_model(model_path)
    features = training.iloc[[0, 1, 2]].copy()
    baseline, contributions = tree_probability_contributions(loaded, features)
    roots = [tree.tree_.value[0, 0] for tree in loaded.estimators_]
    assert baseline == pytest.approx(np.mean([root[1] / root.sum() for root in roots]), rel=0, abs=1e-12)
    assert contributions.shape == (3, 6)
    np.testing.assert_array_equal(contributions[:, 1:], np.zeros((3, 5)))
    np.testing.assert_allclose(baseline + contributions.sum(axis=1), loaded.predict_proba(features)[:, 1], rtol=0, atol=1e-12)


@pytest.mark.parametrize("kind", ["missing", "directory", "empty", "extension"])
def test_invalid_demo_input(analysis_inputs, tmp_path, kind):
    _, model_path, _ = analysis_inputs
    path = tmp_path / ("bad.txt" if kind == "extension" else "bad.dem")
    if kind == "directory":
        path.mkdir()
    elif kind == "empty":
        path.touch()
    elif kind == "extension":
        path.write_bytes(b"not a demo")
    with pytest.raises((FileNotFoundError, ValueError)):
        analyze_demo(path, model_path, tmp_path / "invalid_input")
    assert not (tmp_path / "invalid_input").exists()


def test_cli_analysis_and_default_output(analysis_inputs, tmp_path, monkeypatch, capsys):
    demo_path, model_path, _ = analysis_inputs
    monkeypatch.chdir(tmp_path)
    assert main(["analyze", str(demo_path), "--model", str(model_path)]) == 0
    captured = capsys.readouterr()
    assert not captured.err
    assert "Match Analysis: match | partial" in captured.out
    assert "Players: 2/5 scored; windows: 4" in captured.out
    assert "uncalibrated" in captured.out and "N/A (insufficient data)" in captured.out
    assert (tmp_path / "match_analysis" / "report.json").is_file()
    assert (tmp_path / "match_analysis" / "report.md").is_file()


def test_cli_preserves_unicode_identity_with_legacy_output(analysis_inputs, tmp_path, monkeypatch):
    demo_path, model_path, backend = analysis_inputs
    backend.roster.loc[backend.roster["steamid"].eq(1), "name"] = "Alpha \u2661"
    buffer = io.BytesIO()
    output = io.TextIOWrapper(buffer, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", output)
    directory = tmp_path / "unicode"
    assert main(["analyze", str(demo_path), "--model", str(model_path), "--output", str(directory)]) == 0
    output.flush()
    assert b"Alpha \\u2661" in buffer.getvalue()
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    assert next(p for p in report["players"] if p["source_player_id"] == "1")["player_name"] == "Alpha \u2661"


@pytest.mark.parametrize("shot_weapon,contact_weapon", [("weapon_ak47", "ak47"), ("ak47", "weapon_ak47")])
def test_event_weapon_prefix_does_not_exclude_tracking(analysis_inputs, tmp_path, shot_weapon, contact_weapon):
    demo_path, model_path, backend = analysis_inputs
    backend.events["weapon_fire"]["weapon"] = shot_weapon
    for event in ("player_hurt", "player_death"):
        backend.events[event]["weapon"] = contact_weapon
    report = analyze_demo(demo_path, model_path, tmp_path / "weapon_prefix")
    window = next(w for w in report["windows"] if w["player_id"] == "demo:1" and w["shot_tick"] == 131)
    assert [e["event_type"] for e in window["events"]] == ["shot", "hit", "kill"]
    assert window["weapon"] == shot_weapon
    assert window["visualization"]["reference"] == "observed_victim_position"
    assert window["visualization"]["tracking"]["mean_error_degrees"] == pytest.approx(15.5)
    assert window["score"] == 0.0


@pytest.mark.parametrize("round_ticks,expected_round,expected_boundary", [
    ((100, 160), 1, False),  # Entirely inside, including the start tick.
    ((100, 131), 1, False),  # End tick is inclusive.
    ((100, 115), None, True),  # Completed round followed by a transition.
    ((110, 120), None, True),  # Both endpoints unknown, but a round lies inside.
    ((110, 160), 1, True),  # Crosses a start tick.
    ((50, 99), None, False),  # Entirely between completed rounds.
])
def test_round_window_boundaries(analysis_inputs, tmp_path, round_ticks, expected_round, expected_boundary):
    demo_path, model_path, backend = analysis_inputs
    backend.events["begin_new_match"]["tick"] = 50
    backend.events["round_start"] = pd.DataFrame({"tick": [50, round_ticks[0], 200]})
    backend.events["round_end"] = pd.DataFrame({"tick": [60, round_ticks[1], 260],
                                               "winner": ["CT"] * 3, "reason": ["t_killed"] * 3})
    # The first completed round is 50..60; the tested round has number 2.
    if round_ticks == (50, 99):
        backend.events["round_end"] = backend.events["round_end"].iloc[[1, 2]]
    report = analyze_demo(demo_path, model_path, tmp_path / "boundaries")
    window = next(w for w in report["windows"] if w["player_id"] == "demo:1" and w["shot_tick"] == 131)
    assert window["round_number"] == (2 if expected_round else None)
    assert window["crosses_round_boundary"] is expected_boundary


@pytest.mark.parametrize("victim_samples", [0, 1, "duplicate"])
def test_linked_victim_without_usable_telemetry(analysis_inputs, tmp_path, victim_samples):
    demo_path, model_path, backend = analysis_inputs
    target = backend.ticks[backend.ticks["steamid"].eq(2) & backend.ticks["tick"].between(100, 131)]
    backend.ticks = backend.ticks.drop(target.index)
    if victim_samples == "duplicate":
        backend.ticks = pd.concat([backend.ticks, target, target], ignore_index=True)
    elif victim_samples:
        backend.ticks = pd.concat([backend.ticks, target.iloc[:victim_samples]], ignore_index=True)
    report = analyze_demo(demo_path, model_path, tmp_path / "missing_target")
    window = next(w for w in report["windows"] if w["player_id"] == "demo:1" and w["shot_tick"] == 131)
    assert [e["event_type"] for e in window["events"]] == ["shot", "hit", "kill"]
    assert window["visualization"]["reference"] == "shot_aim_direction"
    assert window["visualization"]["tracking"] is None
    assert window["visualization"]["tracking_unavailable_reason"] == "Fewer than two concurrent samples for the linked victim"
    assert window["visualization"]["sample_count"] == 32


def test_scored_windows_without_any_round_context(analysis_inputs, tmp_path):
    demo_path, model_path, backend = analysis_inputs
    backend.events["round_start"] = backend.events["round_start"].iloc[:0]
    backend.events["round_end"] = backend.events["round_end"].iloc[:0]
    report = analyze_demo(demo_path, model_path, tmp_path / "no_round_context")
    assert report["summary"]["status"] == "partial"
    assert report["summary"]["missing_round_window_count"] == 4
    assert report["summary"]["cross_round_window_count"] == 0
    assert report["rounds"] == []
    assert all(w["round_number"] is None for w in report["windows"])
    assert [p["score"] for p in report["players"][:2]] == [1.0, 0.5]


@pytest.mark.parametrize("end_tick,event_types", [
    (131, ["shot"]), (132, ["shot", "hit"]), (133, ["shot", "hit", "kill"]),
])
def test_linked_events_respect_inclusive_round_end(analysis_inputs, tmp_path, end_tick, event_types):
    demo_path, model_path, backend = analysis_inputs
    backend.events["round_end"].loc[0, "tick"] = end_tick
    report = analyze_demo(demo_path, model_path, tmp_path / "event_bounds")
    window = next(w for w in report["windows"] if w["player_id"] == "demo:1" and w["shot_tick"] == 131)
    assert window["round_number"] == 1
    assert [e["event_type"] for e in window["events"]] == event_types
    assert all(e["player_id"] == "demo:1" for e in window["events"])


def test_cli_no_windows_and_parser_error(analysis_inputs, tmp_path, capsys):
    demo_path, model_path, backend = analysis_inputs
    backend.events["weapon_fire"] = backend.events["weapon_fire"].iloc[:0]
    output = tmp_path / "cli_empty"
    args = ["analyze", str(demo_path), "--model", str(model_path), "--output", str(output)]
    assert main(args) == 2
    assert "insufficient_data" in capsys.readouterr().out
    assert (output / "report.json").is_file()
    backend.events["begin_new_match"] = backend.events["begin_new_match"].iloc[:0]
    assert main(args) == 2
    captured = capsys.readouterr()
    assert "Unable to find the beginning of the match." in captured.err
    assert "Traceback" not in captured.err


def test_cli_missing_model_and_required_arguments(analysis_inputs, tmp_path, capsys):
    demo_path, _, _ = analysis_inputs
    assert main(["analyze", str(demo_path), "--model", str(tmp_path / "missing.joblib")]) == 2
    assert "Model bundle file not found" in capsys.readouterr().err
    with pytest.raises(SystemExit) as error:
        main(["analyze", str(demo_path)])
    assert error.value.code == 2
    assert "--model" in capsys.readouterr().err


def test_module_cli_help():
    result = subprocess.run([sys.executable, "-m", "cs2guard_demo", "--help"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "cs2guard" in result.stdout and "analyze" in result.stdout


def test_installed_cli_help():
    executable = Path(sys.executable).with_name("cs2guard.exe" if sys.platform == "win32" else "cs2guard")
    if not executable.is_file():
        pytest.skip("Console script requires project installation")
    result = subprocess.run([str(executable), "--help"], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "cs2guard" in result.stdout and "analyze" in result.stdout
