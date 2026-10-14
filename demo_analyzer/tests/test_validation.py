"""Synthetic checks for external evaluation, independent of local demo data."""

import json
from pathlib import Path

from matplotlib.image import imread
import numpy as np
import pandas as pd
import pytest

import cs2guard_demo.validation as validation
from cs2guard_demo.analysis import analyze_demo
from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS
from demo_analyzer.tests.test_analysis import analysis_inputs  # Reuse the controlled M1–M6 fixture.


def synthetic_report(demo):
    players = []
    windows = []
    for pid, scores in [("demo:1", [.2, .4]), ("demo:2", [.8]), ("demo:3", [])]:
        players.append({"player_id": pid, "source_player_id": pid.split(":")[1], "player_name": "Name | 中文",
                        "score": float(np.mean(scores)) if scores else None, "window_count": len(scores),
                        "shot_count": len(scores), "unscored_shot_count": 0,
                        "status": "scored" if scores else "insufficient_data", "model_contributions": None})
        for index, score in enumerate(scores):
            windows.append({"window_id": f"{pid}:{index}", "player_id": pid, "score": score,
                            "features": {f: float(index + 1) for f in FEATURE_COLUMNS},
                            "round_number": 1 if index == 0 else None, "crosses_round_boundary": index == 1})
    return {"match": {"match_id": demo.stem, "demo_path": str(demo.resolve()), "map_name": "de_test"},
            "model": {"features": FEATURE_COLUMNS, "window_size": 32, "tick_rate": 64.0},
            "summary": {"player_count": 3, "scored_player_count": 2, "window_count": 3, "round_count": 1,
                        "missing_round_window_count": 1, "cross_round_window_count": 1, "status": "partial"},
            "players": players, "windows": windows}


@pytest.fixture
def benchmark(tmp_path, monkeypatch):
    directory = tmp_path / "external"
    directory.mkdir()
    for name in ["b.dem", "a.dem"]:
        (directory / name).write_bytes(name.encode())
    model = tmp_path / "rf.joblib"
    model.write_bytes(b"frozen synthetic bundle")
    model.with_suffix(".json").write_text("{}")
    (tmp_path / "pyproject.toml").write_text("# synthetic source snapshot\n")
    calls = []
    monkeypatch.setattr(validation, "load_analysis_model", lambda _: (None, {}))
    monkeypatch.setattr(validation, "verify_saved_scores", lambda model, windows, reports: {"status": "synthetic_fixture"})

    def analyze(demo, model, output, *, review_plots):
        assert not review_plots
        calls.append(demo.name)
        if demo.name.startswith("broken"):
            raise ValueError("controlled parsing failure")
        report = synthetic_report(demo)
        validation.write_json(output / "report.json", report)
        (output / "report.md").write_text("Synthetic report", encoding="utf-8")
        return report

    monkeypatch.setattr(validation, "analyze_demo", analyze)
    return directory, model, tmp_path / "outputs", tmp_path, calls


def run_benchmark(benchmark, **kwargs):
    directory, model, output, root, _ = benchmark
    return validation.run_evaluation(directory, model, output, root=root, draws=200, **kwargs)


def test_discovery_order_empty_and_invalid_files(tmp_path):
    assert validation.discover_demos(tmp_path) == ([], [])
    (tmp_path / "z.dem").write_bytes(b"z")
    (tmp_path / "a.DEM").write_bytes(b"a")
    (tmp_path / "zero.dem").touch()
    (tmp_path / "wrong.txt").write_text("text")
    demos, rejected = validation.discover_demos(tmp_path)
    assert [p.name for p in demos] == ["a.DEM", "z.dem"]
    assert len(rejected) == 2
    assert validation.discover_demos(tmp_path / "absent")[1]


def test_exact_hash_duplicates_and_history(tmp_path):
    a, b, c = [tmp_path / name for name in ["a.dem", "b.dem", "c.dem"]]
    a.write_bytes(b"same")
    b.write_bytes(b"same")
    c.write_bytes(b"other")
    audit = validation.independence_audit([a, c], [b])
    assert len(audit["exact_duplicates"]) == 1
    assert audit["exact_duplicates"][0]["paths"] == [str(a), str(b)]


def test_labels_identities_unknown_and_missing_scores(tmp_path):
    demo = tmp_path / "a.dem"
    demo.write_bytes(b"demo")
    label = {"players": {"demo:2": {"status": "unknown"}}}
    players, _ = validation.report_tables(synthetic_report(demo), label)
    frame = pd.DataFrame(players)
    assert frame.player_id.tolist() == ["demo:1", "demo:2", "demo:3"]
    assert frame.source_player_id.tolist() == ["1", "2", "3"]
    assert frame.player_name.iloc[0] == "Name | 中文"
    assert np.isnan(frame.score.iloc[2])
    rates = validation.flag_rates(frame, draws=200)
    at_half = next(r for r in rates if r["threshold"] == .5)
    assert at_half["evaluable_player_matches"] == 1
    assert at_half["flagged_player_matches"] == 0
    assert at_half["excluded_uncertain_labels"] == 1
    assert at_half["excluded_insufficient_data_known_labels"] == 1
    with pytest.raises(ValueError, match="absent from roster"):
        validation.report_tables(synthetic_report(demo), {"players": {"demo:99": {"status": "unknown"}}})


@pytest.mark.parametrize("entry", [
    {"status": "legitimate"}, {"status": "confirmed_legitimate"},
    {"players": {"1": {"status": "unknown"}}}, {"players": {"demo:1": {}}},
    {"players": {"demo:1": {"status": "unknown", "typo": 1}}}, {"typo": 1},
])
def test_manifest_rejects_uncertain_contract(tmp_path, entry):
    demo = tmp_path / "a.dem"
    demo.write_bytes(b"demo")
    manifest = tmp_path / "labels.json"
    validation.write_json(manifest, {demo.name: entry})
    with pytest.raises(ValueError):
        validation.load_labels(manifest, [demo], tmp_path)


def test_manifest_individual_confirmation_and_path_check(tmp_path):
    demo = tmp_path / "a.dem"
    demo.write_bytes(b"demo")
    manifest = tmp_path / "labels.json"
    label = {"a.dem": {"status": "presumed_legitimate", "players": {
        "demo:1": {"status": "confirmed_legitimate", "evidence": "Individual controlled recording"},
        "demo:2": {"status": "unknown"}}}}
    validation.write_json(manifest, label)
    assert validation.load_labels(manifest, [demo], tmp_path) == label
    validation.write_json(manifest, {"not_present.dem": {"status": "unknown"}})
    with pytest.raises(ValueError, match="relative demo"):
        validation.load_labels(manifest, [demo], tmp_path)


def test_descriptive_nonfinite_small_sample_percentiles():
    stats = validation.descriptive([1, 2, 3, 4, None, np.nan, np.inf, -np.inf, "bad"])
    assert stats["finite"] == 4 and stats["missing_or_nonfinite"] == 5
    assert stats["mean"] == stats["median"] == 2.5
    assert stats["std"] == pytest.approx(np.std([1, 2, 3, 4], ddof=1))
    assert stats["q25"] == 1.75 and stats["q75"] == 3.25
    assert stats["p99"] == pytest.approx(3.97)
    assert stats["tail_percentiles_exploratory"]
    assert validation.descriptive([7])["std"] is None
    assert validation.descriptive([])["mean"] is None
    assert validation.descriptive([np.inf])["finite"] == 0


@pytest.mark.parametrize("score, expected", [(0, 0), (.5, 4), (1, 4)])
def test_flags_ties_zero_all_and_iid_sensitivity(score, expected):
    players = pd.DataFrame({"match_id": ["a", "a", "b", "b"], "player_id": ["1", "2", "3", "4"],
                            "label_status": ["presumed_legitimate"] * 4, "score": [score] * 4, "window_count": [1] * 4})
    row = next(r for r in validation.flag_rates(players, draws=200) if r["threshold"] == .5)
    assert row["flagged_player_matches"] == expected
    assert row["presumed_legitimate_flag_rate"] == expected / 4
    assert row["flagged_matches"] == (2 if expected else 0)
    assert row["flagged_match_rate"] == (1 if expected else 0)
    assert row["match_bootstrap"]["degenerate"]
    assert row["match_bootstrap"]["interval"] == [expected / 4] * 2
    interval = row["iid_wilson_sensitivity_only"]
    assert interval[1] > 0 and interval[0] < 1
    assert validation.THRESHOLDS == tuple(i / 10 for i in range(1, 10))


def test_exact_flag_proportions_with_nonfinite_and_unscored():
    players = pd.DataFrame({"match_id": ["a"] * 6 + ["b"], "player_id": list("1234567"),
                            "label_status": ["presumed_legitimate"] * 5 + ["unknown", "confirmed_legitimate"],
                            "score": [.5, .49, np.inf, np.nan, 0, .9, .7], "window_count": [2, 2, 2, 0, 0, 2, 2]})
    half = validation.flag_rates(players, draws=200)[4]
    assert half["evaluable_player_matches"] == 3
    assert half["flagged_player_matches"] == 2
    assert half["presumed_legitimate_flag_rate"] == pytest.approx(2 / 3)
    assert half["excluded_uncertain_labels"] == 1
    assert half["excluded_insufficient_data_known_labels"] == 3
    assert half["by_match"] == [{"match_id": "a", "flagged": 1, "evaluable": 2, "rate": .5},
                                {"match_id": "b", "flagged": 1, "evaluable": 1, "rate": 1.0}]


def test_cluster_bootstrap_resamples_match_ratio_reproducibly():
    values, groups = [0, 0, 1], ["a", "a", "b"]
    first = validation.cluster_mean_ci(values, groups, draws=500)
    assert first == validation.cluster_mean_ci(values, groups, draws=500)
    assert first["groups"] == 2 and first["interval"] == [0, 1]
    assert validation.cluster_mean_ci([0, 1], ["same", "same"], draws=200)["interval"] is None
    assert validation.cluster_mean_ci([], [], draws=200)["interval"] is None
    with pytest.raises(ValueError):
        validation.cluster_mean_ci(values, groups, draws=1)


def test_repeated_players_connected_components():
    players = pd.DataFrame({"match_id": ["a", "b", "b", "c", "d"], "player_id": ["1", "1", "2", "2", "3"]})
    components = validation.connected_matches(players)
    assert components == {"a": "a", "b": "a", "c": "a", "d": "d"}
    assert len(set(validation.connected_matches(players.iloc[:-1]).values())) == 1


def test_feature_shift_missing_nonfinite_and_player_units():
    external = pd.DataFrame({"f": [1, np.inf, np.nan, 3]})
    reference = pd.DataFrame({"f": [0, 1, 2, 3, 4]})
    result = validation.compare_distributions(external, reference, ["f", "absent"])
    assert result["f"]["external"]["missing_or_nonfinite"] == 2
    assert result["f"]["median_shift_in_reference_iqr"] == 0
    assert len(result["f"]["external_quantiles"]) == 101
    assert result["absent"]["median_shift_in_reference_iqr"] is None
    assert result["absent"]["external"]["missing_or_nonfinite"] == 4


def test_existing_cs2cd_comparison_uses_frozen_model_and_historical_split(tmp_path, monkeypatch):
    rows = []
    for match in range(10):
        for label, pid in [("legitimate", "Player_1"), ("suspicious", "Player_2")]:
            for shot in range(2):
                rows.append({"source": "cs2cd", "match_id": f"cs2cd_{match}", "player_id": f"cs2cd:{match}:{pid}",
                             "source_player_id": pid, "identity_scope": "match", "label": label,
                             "window_id": f"{match}:{pid}:{shot}", "shot_tick": shot,
                             **{f: float(match + shot) for f in FEATURE_COLUMNS}})
    path = tmp_path / "reference.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    class FrozenModel:
        classes_ = [0, 1]
        def predict_proba(self, features):
            return np.tile([.75, .25], (len(features), 1))
    monkeypatch.setattr(validation, "load_analysis_model", lambda _: (FrozenModel(), {}))
    players, windows = validation.report_tables(synthetic_report(tmp_path / "a.dem"), {})
    result = validation.reference_comparison(path, tmp_path / "unused.joblib", pd.DataFrame(windows), pd.DataFrame(players), tmp_path)
    assert result["status"] == "available"
    assert result["full_reference_windows"] == 20
    assert result["full_reference_player_matches"] == 10
    assert result["test_reference_windows"] == 4
    assert result["test_reference_player_matches"] == 2
    assert result["m5_input_source_window_counts"] == {"cs2cd": 40}
    assert result["m5_input_observable_overlap"]["match_ids"] == []
    assert result["player_match_scores_test_cs2cd"]["score"]["reference"]["mean"] == .25
    assert result["test_reference_flag_rates"][4]["flagged"] == 0
    assert (tmp_path / "cs2cd_test_player_scores.csv").is_file()


def test_bad_reference_and_missing_map_do_not_invent_values(tmp_path):
    path = tmp_path / "reference.csv"
    path.write_text("not_a_reference\n1\n")
    demo = tmp_path / "a.dem"
    report = synthetic_report(demo)
    report["match"]["map_name"] = None
    players, windows = validation.report_tables(report, {})
    assert validation.reference_comparison(path, tmp_path / "unused", pd.DataFrame(windows), pd.DataFrame(players), tmp_path)["status"] == "unavailable"
    summary = validation.summarize(pd.DataFrame(players), pd.DataFrame(windows), [{"status": "partial"}], draws=200)
    assert summary["per_map"][0]["map_name"] is None
    json.dumps(summary, allow_nan=False)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -.1, 1.1, None])
def test_cache_rejects_invalid_window_score(tmp_path, bad):
    demo = tmp_path / "a.dem"
    report = synthetic_report(demo)
    report["windows"][0]["score"] = bad
    with pytest.raises((ValueError, TypeError)):
        validation.validate_report(report, demo)


@pytest.mark.parametrize("change", ["mean", "identity", "window_count", "null", "features"])
def test_cache_rejects_changed_contract(tmp_path, change):
    demo = tmp_path / "a.dem"
    report = synthetic_report(demo)
    if change == "mean":
        report["players"][0]["score"] = .99
    elif change == "identity":
        report["windows"][0]["player_id"] = "demo:absent"
    elif change == "window_count":
        report["players"][0]["window_count"] += 1
    elif change == "null":
        report["players"][-1]["score"] = 0
    else:
        report["model"]["features"] = list(reversed(FEATURE_COLUMNS))
    with pytest.raises(ValueError):
        validation.validate_report(report, demo)


def test_batch_reports_resume_and_model_integrity(benchmark):
    _, model, output, _, calls = benchmark
    before = validation.sha256(model), validation.sha256(model.with_suffix(".json"))
    run = run_benchmark(benchmark)
    result = json.loads((run / "evaluation.json").read_text(encoding="utf-8"))
    assert calls == ["a.dem", "b.dem"]
    counts = result["statistics"]["counts"]
    assert counts["demos_evaluated"] == 2
    assert counts["player_matches_detected"] == 6 and counts["player_matches_scored"] == 4
    assert counts["windows"] == 6 and counts["connected_match_components"] == 1
    assert len(result["statistics"]["repeated_players"]) == 2
    assert result["statistics"]["eligible_score_mean_connected_bootstrap"]["interval"] is None
    assert result["comparison"]["status"] == "unavailable"
    assert (run / "source_snapshot.zip").is_file()
    assert (run / "report.md").is_file() and "not an established FPR" in (run / "report.md").read_text(encoding="utf-8")
    for name in result["figures"]:
        assert imread(run / name).shape[0] > 300
    old = result["statistics"]
    assert run_benchmark(benchmark) == run
    assert calls == ["a.dem", "b.dem"]
    repeated = json.loads((run / "statistics.json").read_text(encoding="utf-8"))
    assert repeated == old
    assert before == (validation.sha256(model), validation.sha256(model.with_suffix(".json")))
    assert all(i["cache_reused"] for i in json.loads((run / "inventory.json").read_text(encoding="utf-8")))
    assert json.loads((output / "latest.json").read_text())["run_directory"] == str(run)


def test_corrupt_cache_new_attempt_preserves_old(benchmark):
    run = run_benchmark(benchmark)
    inventory = json.loads((run / "inventory.json").read_text(encoding="utf-8"))
    old_path = Path(inventory[0]["report_path"]) / "report.json"
    old_path.write_text("corrupt")
    run_benchmark(benchmark)
    assert benchmark[-1] == ["a.dem", "b.dem", "a.dem"]
    assert old_path.read_text() == "corrupt"
    latest = json.loads((run / "inventory.json").read_text(encoding="utf-8"))
    assert latest[0]["report_path"].endswith("attempt-0002")


def test_batch_empty_folder_and_parser_errors(benchmark):
    directory, _, _, _, _ = benchmark
    for path in directory.glob("*.dem"):
        path.unlink()
    run = run_benchmark(benchmark)
    result = json.loads((run / "statistics.json").read_text())
    assert result["counts"]["demos_evaluated"] == 0
    assert result["eligible_player_match_scores"]["mean"] is None
    assert result["flag_rates"][4]["presumed_legitimate_flag_rate"] is None
    (directory / "broken.dem").write_bytes(b"broken")
    run = run_benchmark(benchmark)
    result = json.loads((run / "evaluation.json").read_text())
    assert result["statistics"]["counts"]["demos_excluded_or_failed"] == 1
    assert "controlled parsing failure" in result["inventory"][0]["reason"]


def test_batch_duplicate_exclusion(benchmark):
    directory = benchmark[0]
    (directory / "c.dem").write_bytes((directory / "a.dem").read_bytes())
    run = run_benchmark(benchmark)
    result = json.loads((run / "statistics.json").read_text())
    assert result["counts"]["demos_available"] == 3
    assert result["counts"]["demos_evaluated"] == 2
    assert result["counts"]["demos_excluded_or_failed"] == 1


def test_batch_source_model_change_invalidates_cache(benchmark):
    first = run_benchmark(benchmark)
    benchmark[0].joinpath("a.dem").write_bytes(b"new source")
    second = run_benchmark(benchmark)
    assert first != second
    assert benchmark[-1] == ["a.dem", "b.dem", "a.dem"]
    benchmark[1].write_bytes(b"new frozen model")
    third = run_benchmark(benchmark)
    assert third != second
    assert benchmark[-1] == ["a.dem", "b.dem", "a.dem", "a.dem", "b.dem"]


def test_batch_detects_mid_run_model_mutation(benchmark, monkeypatch):
    original = validation.analyze_demo
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        benchmark[1].write_bytes(b"changed during run")
        return result
    monkeypatch.setattr(validation, "analyze_demo", mutate)
    with pytest.raises(RuntimeError, match="bundle changed"):
        run_benchmark(benchmark)


def test_batch_rejects_training_directory_and_source_output(benchmark):
    directory, model, output, root, _ = benchmark
    with pytest.raises(ValueError, match="separate"):
        validation.run_evaluation(directory, model, directory / "reports", root=root)
    with pytest.raises(ValueError, match="training source"):
        validation.run_evaluation(root / "demo_analyzer/data/raw/train_sources/demo", model, output, root=root)
    with pytest.raises(ValueError, match="raw source"):
        validation.run_evaluation(directory, model, root / "demo_analyzer/data/raw/new_outputs", root=root)


def test_m6_batch_option_preserves_scores_without_review_figures(analysis_inputs, tmp_path, monkeypatch):
    demo, model, _ = analysis_inputs
    monkeypatch.setattr("cs2guard_demo.analysis._plot_review_window", lambda *a: pytest.fail("Batch must skip review plots"))
    report = analyze_demo(demo, model, tmp_path / "batch", review_plots=False)
    assert [p["score"] for p in report["players"]] == [1.0, .5, None, None, None]
    assert report["summary"]["window_count"] == 4
    assert not list((tmp_path / "batch").glob("*.png"))
    assert all(w["visualization"]["path"] is None for w in report["review_events"])
    _, windows = validation.report_tables(report, {})
    checked = validation.verify_saved_scores(model, pd.DataFrame(windows), [report])
    assert checked["status"] == "verified"
    assert checked["max_absolute_score_difference"] <= 1e-12
    assert checked["max_contribution_reconstruction_error"] <= 1e-12
    changed = pd.DataFrame(windows)
    changed.loc[0, "score"] = .123
    with pytest.raises(ValueError, match="scores differ"):
        validation.verify_saved_scores(model, changed, [report])
