"""Frozen M6 evaluation on presumed-legitimate demos; never fits a model.

Run from the repository root: python -m cs2guard_demo.validation --help.
The match is the resampling unit. Window comparisons are descriptive only.
"""

import argparse
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import subprocess
import zipfile

import numpy as np
import pandas as pd

from cs2guard_demo.analysis import analyze_demo, load_analysis_model, TICK_RATE, WINDOW_SIZE
from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS, prepare_features
from cs2guard_demo.supervised import aggregate_player_scores, split_labeled_dataset

# Historical descriptive grid, fixed before looking at external scores.
THRESHOLDS = tuple(i / 10 for i in range(1, 10))
STATUSES = {"presumed_legitimate", "confirmed_legitimate", "unknown"}
PLAYER_COLUMNS = ["match_id", "map_name", "player_id", "source_player_id", "player_name",
                  "label_status", "label_evidence", "score", "window_count", "shot_count",
                  "unscored_shot_count", "status", "missing_round_window_count", "cross_round_window_count"]
WINDOW_COLUMNS = ["match_id", "player_id", "window_id", "score", *FEATURE_COLUMNS]
LIMITATIONS = [
    "Labels default to presumed_legitimate solely from the user's declaration; no independent player adjudication exists.",
    "Scores are arithmetic means of uncalibrated class-1 outputs, not probabilities of cheating. High scores identify review cases only.",
    "Thresholds 0.10–0.90 reuse scripts/analyze_supervised_thresholds.py; >= includes ties as in M5. 0.50 is historical, not operationally validated.",
    "Player-match observations receive equal weight. Overlapping windows are dependent and never used as independent CI observations.",
    "95% percentile match-bootstrap CIs (seed 42, 5000 draws by default) are exploratory with few matches. Repeated players violate match independence.",
    "Connected-match bootstrap additionally groups matches sharing a persistent player ID. Fewer than two components gives no CI; residual dependence is unknown.",
    "Wilson intervals are IID sensitivity benchmarks only, not dependence-adjusted confidence bounds. A zero/all flag bootstrap is degenerate and provides no population bound.",
    "Zero observed flags does not imply zero population flag rate. Unknown labels and unscored players are excluded from flag denominators but retained descriptively.",
    "CS2CD IDs are anonymous and match scoped. Different demo hashes do not prove independence of matches, sessions or real players from CS2CD.",
    "CS2CD comparisons use the existing extraction protocol and fixed historical M5 test split. Feature/window weighting differs from equal-weight player-match summaries.",
    "No external reliable positives: recall, ROC-AUC and PR-AUC cannot be evaluated here. Distribution shifts do not establish detection degradation.",
    "No external calibration, retraining, threshold optimization or demonstrated generalization. No minimum window count has been validated.",
    "M6 preserves historical 32-tick/64-Hz windows, including absent/crossing round context. Partial reports are included with explicit quality counts.",
    "Feature missing-value fractions describe retained windows only; M6 reports do not enumerate every raw telemetry row discarded upstream.",
]


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def digest_json(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def discover_demos(directory: Path) -> tuple[list[Path], list[dict]]:
    if not directory.is_dir():
        return [], [{"path": str(directory.resolve()), "reason": "Input directory absent"}]
    demos, rejected = [], []
    for path in sorted(directory.rglob("*"), key=lambda p: p.relative_to(directory).as_posix()):
        if not path.is_file():
            continue
        if path.suffix.lower() != ".dem" or not path.stat().st_size:
            rejected.append({"path": str(path.resolve()), "reason": "Expected a non-empty .dem file"})
        else:
            demos.append(path)
    return demos, rejected


def load_labels(path: Path | None, demos: list[Path], directory: Path) -> dict:
    """Optional JSON: {relative_demo: {status, evidence, players: {canonical_id: {status, evidence}}}}."""
    labels = json.loads(path.read_text(encoding="utf-8")) if path else {}
    names = {p.relative_to(directory).as_posix() for p in demos}
    if not isinstance(labels, dict) or set(labels) - names:
        raise ValueError("Manifest must be an object keyed by discovered relative demo paths")
    for entry in labels.values():
        if not isinstance(entry, dict) or set(entry) - {"status", "evidence", "players"}:
            raise ValueError("Invalid demo label entry")
        if entry.get("status") == "confirmed_legitimate":
            raise ValueError("confirmed_legitimate requires individual player overrides")
        overrides = entry.get("players", {})
        if not isinstance(overrides, dict) or any(not str(k).startswith("demo:") for k in overrides):
            raise ValueError("Player overrides require canonical demo:<Steam ID> keys")
        for item in [entry, *overrides.values()]:
            if not isinstance(item, dict) or item.get("status", "presumed_legitimate") not in STATUSES:
                raise ValueError("Invalid label status")
            if not isinstance(item.get("evidence", ""), str):
                raise ValueError("Label evidence must be text")
            if item.get("status") == "confirmed_legitimate" and not item.get("evidence", "").strip():
                raise ValueError("confirmed_legitimate requires individual evidence")
        for item in overrides.values():
            if set(item) - {"status", "evidence"} or "status" not in item:
                raise ValueError("Player overrides require status and optional evidence")
    return labels


def descriptive(values) -> dict:
    raw = pd.to_numeric(pd.Series(values, dtype=object), errors="coerce")
    finite = raw[np.isfinite(raw.astype(float))].astype(float)
    result = {"total": len(raw), "finite": len(finite), "missing_or_nonfinite": len(raw) - len(finite),
              "missing_or_nonfinite_rate": (len(raw) - len(finite)) / len(raw) if len(raw) else None,
              "tail_percentiles_exploratory": len(finite) < 100}
    if finite.empty:
        return {**result, **dict.fromkeys(["mean", "median", "std", "min", "q25", "q75", "p90", "p95", "p99", "max"])}
    # pandas describe supplies established sample standard deviation and quartiles.
    stats = finite.describe(percentiles=[.25, .5, .75, .90, .95, .99])
    for out, key in {"mean": "mean", "median": "50%", "std": "std", "min": "min", "q25": "25%",
                     "q75": "75%", "p90": "90%", "p95": "95%", "p99": "99%", "max": "max"}.items():
        result[out] = float(stats[key]) if np.isfinite(stats[key]) else None
    return result


def wilson(successes: int, count: int) -> list[float] | None:
    """95% IID sensitivity interval; dependence warnings are mandatory in reports."""
    if not count:
        return None
    z = 1.959963984540054
    p, scale = successes / count, 1 + z * z / count
    center = (p + z * z / (2 * count)) / scale
    width = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / scale
    return [max(0.0, center - width), min(1.0, center + width)]


def connected_matches(players: pd.DataFrame) -> dict[str, str]:
    """Keep all matches sharing observable identities in the same resampling group."""
    parent = {m: m for m in sorted(players.match_id.unique())}

    def root(match):
        while parent[match] != match:
            match = parent[match]
        return match

    for _, rows in players.groupby("player_id", sort=True):
        matches = sorted(rows.match_id.unique())
        for match in matches[1:]:
            a, b = sorted((root(matches[0]), root(match)))
            parent[b] = a
    return {m: root(m) for m in parent}


def cluster_mean_ci(values, groups, *, seed: int = 42, draws: int = 5000) -> dict:
    if draws < 100 or seed < 0:
        raise ValueError("At least 100 bootstrap draws and a nonnegative seed required")
    data = pd.DataFrame({"value": np.asarray(values, dtype=float), "group": list(groups)})
    data = data[np.isfinite(data.value)]
    aggregates = data.groupby("group", sort=True).value.agg(["sum", "count"])
    count = len(aggregates)
    result = {"groups": count, "draws": draws, "seed": seed, "confidence": .95,
              "interval": None, "exploratory": True, "degenerate": False}
    if count < 2:
        return result
    indices = np.random.default_rng(seed).integers(0, count, size=(draws, count))
    means = aggregates["sum"].to_numpy()[indices].sum(axis=1) / aggregates["count"].to_numpy()[indices].sum(axis=1)
    result.update(interval=np.quantile(means, [.025, .975]).tolist(), degenerate=bool(np.ptp(means) == 0))
    return result


def flag_rates(players: pd.DataFrame, *, seed=42, draws=5000) -> list[dict]:
    known = players.label_status.isin({"presumed_legitimate", "confirmed_legitimate"})
    finite = np.isfinite(pd.to_numeric(players.score, errors="coerce")) & players.window_count.gt(0)
    evaluable = players[known & finite]
    components = connected_matches(players)
    rows = []
    for threshold in THRESHOLDS:
        flags = evaluable.score.ge(threshold)
        by_match = evaluable.assign(flag=flags).groupby("match_id", sort=True).flag.agg(["sum", "count", "max"])
        flagged, count = int(flags.sum()), len(evaluable)
        match_count, flagged_matches = len(by_match), int(by_match["max"].sum())
        rows.append({"threshold": threshold, "comparison": ">=", "evaluable_player_matches": count,
                     "flagged_player_matches": flagged, "presumed_legitimate_flag_rate": flagged / count if count else None,
                     "excluded_uncertain_labels": int((~known).sum()),
                     "excluded_insufficient_data_known_labels": int((known & ~finite).sum()),
                     "evaluable_matches": match_count, "matches_without_evaluable_players": int(players.match_id.nunique()) - match_count,
                     "flagged_matches": flagged_matches, "flagged_match_rate": flagged_matches / match_count if match_count else None,
                     "match_bootstrap": cluster_mean_ci(flags.astype(float), evaluable.match_id, seed=seed, draws=draws),
                     "connected_match_bootstrap": cluster_mean_ci(flags.astype(float), evaluable.match_id.map(components), seed=seed, draws=draws),
                     "iid_wilson_sensitivity_only": wilson(flagged, count),
                     "match_iid_wilson_sensitivity_only": wilson(flagged_matches, match_count),
                     "flagged_match_bootstrap": cluster_mean_ci(by_match["max"].astype(float), by_match.index, seed=seed, draws=draws),
                     "by_match": [{"match_id": m, "flagged": int(r["sum"]), "evaluable": int(r["count"]),
                                   "rate": float(r["sum"] / r["count"])} for m, r in by_match.iterrows()]})
    return rows


def report_tables(report: dict, label: dict) -> tuple[list[dict], list[dict]]:
    overrides = label.get("players", {})
    ids = {p["player_id"] for p in report["players"]}
    if set(overrides) - ids:
        raise ValueError(f"Manifest IDs absent from roster: {sorted(set(overrides) - ids)}")
    players, windows = [], []
    for player in report["players"]:
        status = overrides.get(player["player_id"], {}).get("status", label.get("status", "presumed_legitimate"))
        evidence = overrides.get(player["player_id"], {}).get("evidence", label.get("evidence", "User declaration; not independently confirmed"))
        entries = [w for w in report["windows"] if w["player_id"] == player["player_id"]]
        raw_score = player.get("score")
        score = float(raw_score) if raw_score is not None and np.isfinite(float(raw_score)) and entries else None
        players.append({"match_id": report["match"]["match_id"], "map_name": report["match"].get("map_name"),
                        **{k: player.get(k) for k in ["player_id", "source_player_id", "player_name", "window_count", "shot_count", "unscored_shot_count", "status"]},
                        "score": score, "label_status": status, "label_evidence": evidence,
                        "missing_round_window_count": sum(w.get("round_number") is None for w in entries),
                        "cross_round_window_count": sum(bool(w.get("crosses_round_boundary")) for w in entries)})
    for window in report["windows"]:
        windows.append({"match_id": report["match"]["match_id"],
                        **{k: window[k] for k in ["player_id", "window_id", "score"]}, **window["features"]})
    return players, windows


def validate_report(report: dict, demo: Path) -> None:
    """Reject stale/incomplete caches, including changed aggregation or missing identities."""
    if report["match"]["demo_path"] != str(demo.resolve()):
        raise ValueError("Report belongs to another source")
    if report["model"]["features"] != FEATURE_COLUMNS or report["model"]["window_size"] != WINDOW_SIZE or report["model"]["tick_rate"] != TICK_RATE:
        raise ValueError("Incompatible extraction contract")
    players, windows = report["players"], report["windows"]
    ids = [p["player_id"] for p in players]
    if len(ids) != len(set(ids)) or len(players) != report["summary"]["player_count"] or len(windows) != report["summary"]["window_count"]:
        raise ValueError("Invalid report counts/identities")
    if sum(p["window_count"] > 0 for p in players) != report["summary"]["scored_player_count"]:
        raise ValueError("Scored player count mismatch")
    window_ids = [w["window_id"] for w in windows]
    if len(set(window_ids)) != len(window_ids):
        raise ValueError("Duplicate report windows")
    for w in windows:
        if w["player_id"] not in ids or not np.isfinite([w["score"], *[w["features"][f] for f in FEATURE_COLUMNS]]).all() or not 0 <= w["score"] <= 1:
            raise ValueError("Invalid window values/identity")
    for player in players:
        scores = [w["score"] for w in windows if w["player_id"] == player["player_id"]]
        if len(scores) != player["window_count"]:
            raise ValueError("Player window count mismatch")
        if scores:
            if player["score"] is None or not np.isfinite(player["score"]) or not np.isclose(np.mean(scores), player["score"], rtol=1e-12, atol=1e-12):
                raise ValueError("Player score differs from M5 mean")
        elif player["score"] is not None:
            raise ValueError("Unscored player must retain a null score")


def independence_audit(demos: list[Path], historical: list[Path]) -> dict:
    sources = []
    for path in sorted(set(demos + historical)):
        sources.append({"path": str(path.resolve()), "sha256": sha256(path), "size_bytes": path.stat().st_size,
                        "population": "external" if path in demos else "historical_technical"})
    duplicates = []
    for digest in sorted({s["sha256"] for s in sources}):
        group = [s for s in sources if s["sha256"] == digest]
        if len(group) > 1:
            duplicates.append({"sha256": digest, "paths": [s["path"] for s in group]})
    return {"sources": sources, "exact_duplicates": duplicates,
            "training_discovery": "build_dataset.py collects only data/raw/train_sources/demo/*.dem and train_sources/cs2cd/**/*.json; held_out excluded",
            "limitations": "Byte hashes cannot exclude re-exports of the same session. CS2CD anonymization prevents cross-source real-player independence guarantees."}


def freeze_protocol(root: Path, model_path: Path, labels: dict, audit: dict, reference: Path | None,
                    *, seed: int, draws: int) -> dict:
    files = sorted([*root.glob("demo_analyzer/src/**/*.py"), *root.glob("demo_analyzer/scripts/*.py"), root / "pyproject.toml"])
    source_hashes = {p.relative_to(root).as_posix(): sha256(p) for p in files}
    def git(*args):
        result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
        return result.stdout.strip() if result.returncode == 0 else None
    return {"schema_version": 1, "model_path": str(model_path.resolve()), "model_sha256": sha256(model_path),
            "metadata_sha256": sha256(model_path.with_suffix(".json")),
            "git_head": git("rev-parse", "HEAD"), "git_status": git("status", "--short"),
            "source_hashes": source_hashes, "code_sha256": digest_json(source_hashes),
            "python": platform.python_version(), "dependencies": {n: version(n) for n in ["cs2guard", "numpy", "pandas", "scikit-learn", "demoparser2", "matplotlib", "joblib"]},
            "window_size": WINDOW_SIZE, "tick_rate_hz": TICK_RATE, "feature_order": FEATURE_COLUMNS,
            "aggregation": "Arithmetic mean of window scores per player-match; player-matches equally weighted",
            "thresholds": THRESHOLDS, "threshold_origin": "Historical M5 scripts/analyze_supervised_thresholds.py; fixed before external analysis",
            "comparison": ">=", "bootstrap_seed": seed, "bootstrap_draws": draws, "labels": labels,
            "default_label": "presumed_legitimate", "default_evidence": "User declaration only",
            "audit": audit, "reference": {"path": str(reference.resolve()), "sha256": sha256(reference)} if reference and reference.is_file() else None}


def compare_distributions(external: pd.DataFrame, reference: pd.DataFrame, columns: list[str]) -> dict:
    """Descriptive shifts only: no tests pretending overlapping windows are independent."""
    result = {}
    for column in columns:
        a = pd.to_numeric(external.get(column, pd.Series(np.nan, index=external.index)), errors="coerce")
        b = pd.to_numeric(reference.get(column, pd.Series(np.nan, index=reference.index)), errors="coerce")
        sa, sb = descriptive(a), descriptive(b)
        fa, fb = a[np.isfinite(a)], b[np.isfinite(b)]
        iqr = sb["q75"] - sb["q25"] if sb["finite"] else 0
        result[column] = {"external": sa, "reference": sb,
                          "median_shift_in_reference_iqr": (sa["median"] - sb["median"]) / iqr if len(fa) and iqr else None,
                          "external_above_reference_p99_rate": float(fa.gt(sb["p99"]).mean()) if len(fa) and len(fb) else None,
                          "external_quantiles": np.quantile(fa, np.linspace(0, 1, 101)).tolist() if len(fa) else [],
                          "reference_quantiles": np.quantile(fb, np.linspace(0, 1, 101)).tolist() if len(fb) else []}
    return result


def reference_comparison(path: Path | None, model_path: Path, windows: pd.DataFrame, players: pd.DataFrame,
                         output: Path) -> dict:
    if path is None or not path.is_file():
        return {"status": "unavailable", "required_file": str(path) if path else "demo_analyzer/data/processed/supervised_dataset.csv",
                "reason": "Existing CS2CD labeled aim CSV absent; no automatic regeneration"}
    try:
        data = pd.read_csv(path, dtype={c: str for c in ["source", "match_id", "player_id", "source_player_id", "identity_scope", "label"]})
        required = {"source", "match_id", "player_id", "label", *FEATURE_COLUMNS}
        if required - set(data):
            raise ValueError(f"Reference missing columns: {sorted(required - set(data))}")
        source_counts = {str(k): int(v) for k, v in data.source.value_counts(dropna=False).items()}
        dataset_overlap = {"match_ids": sorted({Path(m).stem for m in players.match_id} & set(data.match_id)),
                           "player_ids": sorted(set(players.player_id) & set(data.player_id)),
                           "scope": "All sources in the existing M5 input CSV, checked before filtering CS2CD"}
        data = data[data.source.eq("cs2cd")].copy()
        legitimate = data[data.label.eq("legitimate")]
        if legitimate.empty:
            raise ValueError("No legitimate CS2CD reference windows")
        full_comparison = compare_distributions(windows, legitimate, FEATURE_COLUMNS)
        # Reuse the exact historical split, including both labels before selecting negatives.
        _, test = split_labeled_dataset(data, test_size=.2, random_state=42)
        test = test[test.label.eq("legitimate")].copy()
        model, _ = load_analysis_model(model_path)
        scores = model.predict_proba(prepare_features(test))[:, list(model.classes_).index(1)]
        ref_players = aggregate_player_scores(test, scores, "score")
        test["score"] = scores
        ref_players.to_csv(output / "cs2cd_test_player_scores.csv", index=False)
        feature_players = legitimate.groupby(["match_id", "player_id"], as_index=False)[FEATURE_COLUMNS].mean()
        external_features = windows.groupby(["match_id", "player_id"], as_index=False)[FEATURE_COLUMNS].mean()
        eligible = players[players.label_status.isin({"presumed_legitimate", "confirmed_legitimate"}) & players.score.notna()]
        return {"status": "available", "source_path": str(path.resolve()), "source_sha256": sha256(path),
                "m5_input_source_window_counts": source_counts, "m5_input_observable_overlap": dataset_overlap,
                "full_reference_windows": len(legitimate), "full_reference_player_matches": len(feature_players),
                "test_reference_windows": len(test), "test_reference_player_matches": len(ref_players),
                "test_reference_matches": int(test.match_id.nunique()),
                "window_features_full_cs2cd": full_comparison,
                "player_match_feature_means_full_cs2cd": compare_distributions(external_features, feature_players, FEATURE_COLUMNS),
                "window_features_test_cs2cd": compare_distributions(windows, test, FEATURE_COLUMNS),
                "player_match_scores_test_cs2cd": compare_distributions(eligible, ref_players, ["score"]),
                "window_scores_test_cs2cd": compare_distributions(windows, test, ["score"]),
                "test_reference_flag_rates": [{"threshold": t, "count": len(ref_players), "flagged": int(ref_players.score.ge(t).sum()),
                                                "rate": float(ref_players.score.ge(t).mean())} for t in THRESHOLDS],
                "observable_match_overlap": sorted({Path(m).stem for m in players.match_id} & set(data.match_id)),
                "observable_player_id_overlap": sorted(set(players.player_id) & set(data.player_id)),
                "interpretation": "Full CS2CD features include training and test, descriptive only. Scores compare legitimate historical held-out test player-matches. External feature comparisons include all scored players; label exclusions apply to score/flag comparisons. Match-scoped anonymous CS2CD IDs cannot exclude real-player or session overlap."}
    except (ValueError, KeyError, OSError) as error:
        return {"status": "unavailable", "required_file": str(path.resolve()), "reason": str(error),
                "action": "Provide compatible existing CS2CD labeled aim CSV; no automatic regeneration"}


def summarize(players: pd.DataFrame, windows: pd.DataFrame, inventory: list[dict], *, seed=42, draws=5000) -> dict:
    scored = players[players.score.notna()]
    eligible = scored[scored.label_status.isin({"presumed_legitimate", "confirmed_legitimate"})]
    components = connected_matches(players)
    per_match = []
    for match, rows in players.groupby("match_id", sort=True):
        per_match.append({"match_id": match, "map_name": rows.map_name.iloc[0], "detected": len(rows),
                          "scored": int(rows.score.notna().sum()), "scores": descriptive(rows.score),
                          "window_counts": descriptive(rows.window_count)})
    stability = []
    for pid, rows in scored.groupby("player_id", sort=True):
        if rows.match_id.nunique() > 1:
            stability.append({"player_id": pid, "matches": rows.match_id.tolist(), "scores": rows.score.tolist(),
                              "window_counts": rows.window_count.tolist(), "summary": descriptive(rows.score),
                              "score_range": float(rows.score.max() - rows.score.min())})
    correlation = None
    if len(scored) >= 3 and scored.score.nunique() > 1 and scored.window_count.nunique() > 1:
        correlation = float(scored.score.corr(scored.window_count, method="spearman"))
    return {"counts": {"demos_available": len(inventory), "demos_evaluated": sum(i["status"] in {"complete", "partial", "insufficient_data"} for i in inventory),
                       "demos_excluded_or_failed": sum(i["status"] in {"excluded_duplicate", "error"} for i in inventory),
                       "distinct_observable_players": int(players.player_id.nunique()), "player_matches_detected": len(players),
                       "player_matches_scored": len(scored), "player_matches_unscored": len(players) - len(scored),
                       "presumed_legitimate_evaluable": int(eligible.label_status.eq("presumed_legitimate").sum()),
                       "confirmed_legitimate_evaluable": int(eligible.label_status.eq("confirmed_legitimate").sum()),
                       "unknown_player_matches": int(players.label_status.eq("unknown").sum()), "windows": len(windows),
                       "connected_match_components": len(set(components.values()))},
            "all_player_match_scores": descriptive(players.score), "eligible_player_match_scores": descriptive(eligible.score),
            "eligible_score_mean_match_bootstrap": cluster_mean_ci(eligible.score, eligible.match_id, seed=seed, draws=draws),
            "eligible_score_mean_connected_bootstrap": cluster_mean_ci(eligible.score, eligible.match_id.map(components), seed=seed, draws=draws),
            "window_scores_descriptive_only": descriptive(windows.score), "window_counts_scored_players": descriptive(scored.window_count),
            "window_counts_all_players": descriptive(players.window_count), "per_match": per_match,
            "per_map": [{"map_name": None if pd.isna(name) else name, "matches": int(rows.match_id.nunique()), "scores": descriptive(rows.score)}
                        for name, rows in scored.groupby("map_name", dropna=False, sort=True)],
            "repeated_players": stability, "score_window_count_spearman_descriptive": correlation,
            "flag_rates": flag_rates(players, seed=seed, draws=draws)}


def extreme_cases(players: pd.DataFrame, windows: pd.DataFrame, reports: list[dict]) -> list[dict]:
    cases = []
    for row in players.dropna(subset=["score"]).sort_values(["score", "match_id", "player_id"], ascending=[False, True, True]).head(5).to_dict("records"):
        report = next(r for r in reports if r["match"]["match_id"] == row["match_id"])
        original = next(p for p in report["players"] if p["player_id"] == row["player_id"])
        entries = windows[windows.match_id.eq(row["match_id"]) & windows.player_id.eq(row["player_id"])]
        peers = players[players.match_id.eq(row["match_id"]) & players.player_id.ne(row["player_id"])]
        cases.append({**row, "feature_summary": {f: descriptive(entries[f]) for f in FEATURE_COLUMNS},
                      "model_contributions": original.get("model_contributions"),
                      "peer_mean_score": descriptive(peers.score)["mean"],
                      "completed_round_coverage": 1 - row["missing_round_window_count"] / row["window_count"],
                      "interpretation": "Highest observed scores are review cases, not identified cheaters. RF contributions are path-dependent, not causal or SHAP."})
    return cases


def verify_saved_scores(model_path: Path, windows: pd.DataFrame, reports: list[dict]) -> dict:
    """Reload the frozen model and independently rescore saved features, without fitting."""
    result = {"status": "no_scored_windows", "windows": len(windows), "absolute_tolerance": 1e-12,
              "max_absolute_score_difference": None, "max_contribution_reconstruction_error": None,
              "scope": "Independent model reload/inference on saved features; source parsing is not repeated"}
    if windows.empty:
        return result
    model, _ = load_analysis_model(model_path)
    scores = model.predict_proba(prepare_features(windows))[:, list(model.classes_).index(1)]
    difference = float(np.max(np.abs(scores - windows.score.to_numpy(dtype=float))))
    if difference > 1e-12:
        raise ValueError("Reloaded model scores differ beyond 1e-12")
    errors = []
    for report in reports:
        for record in report["windows"] + report["players"]:
            contribution = record.get("model_contributions")
            if contribution is not None:
                errors.append(abs(contribution["baseline"] + sum(contribution["features"].values()) - record["score"]))
    if errors and max(errors) > 1e-12:
        raise ValueError("RF contributions do not reconstruct saved scores")
    result.update(status="verified", max_absolute_score_difference=difference,
                  max_contribution_reconstruction_error=max(errors) if errors else None)
    return result


def plot_evaluation(players: pd.DataFrame, summary: dict, comparison: dict, output: Path) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    paths = []
    eligible = players[players.label_status.isin({"presumed_legitimate", "confirmed_legitimate"}) & players.score.notna()]
    def save(fig, name):
        fig.tight_layout()
        fig.savefig(output / name, dpi=160)
        plt.close(fig)
        paths.append(name)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(eligible.score, bins=np.linspace(0, 1, 26), color="steelblue", edgecolor="white")
    ax.set(xlabel="Mean class-1 model output (uncalibrated)", ylabel="Player-match count", xlim=(0, 1),
           title=f"Presumed/confirmed legitimate player-matches (n={len(eligible)})\nNo cheating-probability interpretation")
    save(fig, "player_scores.png")

    fig, ax = plt.subplots(figsize=(10, 5))
    groups = list(players.groupby("match_id", sort=True))
    for index, (match, data) in enumerate(groups, 1):
        values = data.score.dropna().to_numpy()
        if len(values):
            ax.boxplot([values], positions=[index], widths=.5, showfliers=False)
            ax.scatter(index + np.linspace(-.15, .15, len(values)), values, s=16, alpha=.7)
    ax.set_xticks(range(1, len(groups) + 1), [f"M{i}" for i in range(1, len(groups) + 1)])
    ax.set(xlabel="Match (ordered IDs in inventory.csv)", ylabel="Player-match mean output", ylim=(0, 1),
           title="All scored player-matches: dispersion by match\nPartial round context retained; repeated players may be dependent")
    save(fig, "scores_by_match.png")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    rates = summary["flag_rates"]
    available = [r for r in rates if r["presumed_legitimate_flag_rate"] is not None]
    x = [r["threshold"] for r in available]
    y = [r["presumed_legitimate_flag_rate"] for r in available]
    ax.plot(x, y, "o-", label="Observed >= threshold")
    if available and all(r["match_bootstrap"]["interval"] for r in available):
        low = [r["match_bootstrap"]["interval"][0] for r in available]
        high = [r["match_bootstrap"]["interval"][1] for r in available]
        ax.fill_between(x, low, high, alpha=.25, label="95% match bootstrap (exploratory)")
    ax.set(xlabel="Historical descriptive threshold (no operational cutoff)", ylabel="Presumed legitimate flag rate", ylim=(-.02, 1.02),
           title="Equal-weight player-match flags\nZero-flag bootstrap is degenerate; repeated players limit independence")
    if available:
        ax.legend()
    save(fig, "flag_rates.png")

    if comparison["status"] == "available":
        fig, axes = plt.subplots(2, 3, figsize=(13, 7))
        for ax, feature in zip(axes.flat, FEATURE_COLUMNS):
            item = comparison["window_features_full_cs2cd"][feature]
            for key, label in [("external_quantiles", "External demos"), ("reference_quantiles", "Full legitimate CS2CD")]:
                quantiles = item[key]
                if quantiles:
                    ax.plot(quantiles, np.linspace(0, 1, len(quantiles)), label=label)
            ax.set_xscale("symlog", linthresh=1)
            unit = "degrees/s²" if "acceleration" in feature else "degrees/s"
            ax.set(title=feature.replace("_angular_", "\nangular "), xlabel=unit, ylabel="Cumulative fraction")
        axes.flat[0].legend(fontsize=8)
        fig.suptitle("Window feature distributions: 101 quantiles, descriptive only\nOverlapping windows; full CS2CD includes training; different player/window weights", fontsize=11)
        fig.subplots_adjust(top=.84)
        fig.tight_layout(rect=(0, 0, 1, .9))
        # Preserve the suptitle margin in the shared save helper.
        fig.savefig(output / "feature_distributions.png", dpi=160)
        plt.close(fig)
        paths.append("feature_distributions.png")
    return paths


def markdown_report(result: dict, output: Path) -> None:
    protocol, summary = result["protocol"], result["statistics"]
    lines = ["# CS2Guard M6 — Presumed-legitimate external evaluation", "",
             "## Protocol", "",
             "This study describes frozen M5/M6 behavior on user-supplied presumed-legitimate demos. It does not validate cheat detection.", "",
             f"Model SHA-256: `{protocol['model_sha256']}`.",
             f"Metadata SHA-256: `{protocol['metadata_sha256']}`.",
             f"Git HEAD: `{protocol['git_head']}`; code SHA-256: `{protocol['code_sha256']}`. Dirty state and exact source archive are recorded in protocol.json/source_snapshot.zip.",
             f"Python {protocol['python']}; dependencies: {json.dumps(protocol['dependencies'])}.",
             "Extraction: 32 unique consecutive player ticks ending at each shot, 64 Hz, unchanged six ordered features. Player score: arithmetic mean of window scores.",
             f"Thresholds fixed before analysis: {list(THRESHOLDS)}, comparator >=; historical M5 descriptive grid, including 0.50. No operational threshold.",
             "Inclusion: valid independent demo bytes with successful M6 output; partial reports retained. Exact duplicates excluded. Unknown labels and missing scores excluded only from flag calculations.",
             f"Bootstrap: {protocol['bootstrap_draws']} draws; seed {protocol['bootstrap_seed']}; 95% percentile intervals by match and connected matches sharing players. No window-level inferential intervals.", "",
             "## Dataset and independence", "", "| Measure | Value |", "|---|---:|"]
    lines.extend(f"| {k} | {v} |" for k, v in summary["counts"].items())
    lines.extend(["", "| Match | Map | Status | Scored/detected | Windows | Rounds | No round | Cross round |", "|---|---|---|---:|---:|---:|---:|---:|"])
    for item in result["inventory"]:
        lines.append(f"| {item['match_id']} | {item.get('map_name')} | {item['status']} | {item.get('scored_player_count', 0)}/{item.get('player_count', 0)} | {item.get('window_count', 0)} | {item.get('round_count')} | {item.get('missing_round_window_count')} | {item.get('cross_round_window_count')} |")
    lines.extend(["", f"Exact duplicate groups: {json.dumps(protocol['audit']['exact_duplicates'])}.",
                  f"Historical technical demo identity/match overlap: {json.dumps(result['historical_overlap'])}.",
                  protocol["audit"]["training_discovery"],
                  "CS2CD native-source hashes are incomparable to re-exported JSON/Parquet. Session IDs are not exposed by M6; anonymous players cannot be reconciled. Independence remains partial.", "",
                  "## Player-match score distribution", "", "| Statistic | Eligible labels | All detected players |", "|---|---:|---:|"])
    for key in ["finite", "missing_or_nonfinite", "mean", "median", "std", "min", "q25", "q75", "p90", "p95", "p99", "max"]:
        lines.append(f"| {key} | {summary['eligible_player_match_scores'][key]} | {summary['all_player_match_scores'][key]} |")
    lines.extend(["", "Standard deviation uses ddof=1; quantiles use linear interpolation. Tail percentiles are exploratory, especially below 100 player-matches.",
                  f"Mean score match bootstrap: {json.dumps(summary['eligible_score_mean_match_bootstrap'])}.",
                  f"Mean score connected-match bootstrap: {json.dumps(summary['eligible_score_mean_connected_bootstrap'])}.",
                  f"Scored player window counts: {json.dumps(summary['window_counts_scored_players'])}.",
                  f"Window score distribution (descriptive only): {json.dumps(summary['window_scores_descriptive_only'])}.",
                  f"Score/window-count Spearman correlation (descriptive): {summary['score_window_count_spearman_descriptive']}.", "",
                  "| Match | Mean | Median | SD | Min | Max |", "|---|---:|---:|---:|---:|---:|"])
    for match in summary["per_match"]:
        lines.append("| " + match["match_id"] + " | " + " | ".join(str(match["scores"][k]) for k in ["mean", "median", "std", "min", "max"]) + " |")
    lines.extend(["", f"Map summaries (small groups, descriptive only): {json.dumps(summary['per_map'])}.",
                  f"Repeated scored players: {len(summary['repeated_players'])}; details in statistics.json and repeated_players.csv.", "",
                  "## Potential false alerts", "",
                  "Metric: presumed_legitimate_flag_rate. Confirmed legitimate observations, if individually documented, are included with separate counts. This is not an established FPR.", "",
                  "| Threshold >= | Flags / evaluable | Rate | Match bootstrap 95% | Connected bootstrap 95% | Flagged / evaluable matches | Excluded labels / insufficient |", "|---:|---:|---:|---|---|---:|---:|"])
    for row in summary["flag_rates"]:
        lines.append(f"| {row['threshold']:.2f} | {row['flagged_player_matches']}/{row['evaluable_player_matches']} | {row['presumed_legitimate_flag_rate']} | {row['match_bootstrap']['interval']} | {row['connected_match_bootstrap']['interval']} | {row['flagged_matches']}/{row['evaluable_matches']} | {row['excluded_uncertain_labels']}/{row['excluded_insufficient_data_known_labels']} |")
    lines.extend(["", "Match-specific flags, flagged-match bootstrap intervals and IID Wilson sensitivity intervals are in statistics.json and threshold_by_match.csv.",
                  "Zero/all observed flags yield degenerate bootstrap intervals. They are not population bounds. Wilson intervals assume independent observations and do not solve shared-match/player dependence.", "",
                  "## CS2CD distribution comparison", ""])
    comparison = result["comparison"]
    if comparison["status"] == "available":
        lines.extend([comparison["interpretation"],
                      f"M5 input source counts: {json.dumps(comparison['m5_input_source_window_counts'])}; observable overlap: {json.dumps(comparison['m5_input_observable_overlap'])}.",
                      f"Full legitimate reference: {comparison['full_reference_windows']} windows, {comparison['full_reference_player_matches']} player-matches. Historical legitimate test: {comparison['test_reference_windows']} windows, {comparison['test_reference_player_matches']} player-matches, {comparison['test_reference_matches']} matches.", "",
                      "| Feature (window unit) | External median | Full CS2CD median | Median shift / reference IQR | External > reference P99 |", "|---|---:|---:|---:|---:|"])
        for feature, item in comparison["window_features_full_cs2cd"].items():
            lines.append(f"| {feature} | {item['external']['median']} | {item['reference']['median']} | {item['median_shift_in_reference_iqr']} | {item['external_above_reference_p99_rate']} |")
        score = comparison["player_match_scores_test_cs2cd"]["score"]
        lines.extend(["", f"Player-match score comparison: external mean/median {score['external']['mean']}/{score['external']['median']}; historical legitimate test {score['reference']['mean']}/{score['reference']['median']}.",
                      "Feature units: speed in degrees/s, acceleration in degrees/s². Full/test window comparisons and equal-weight player-match feature means are separated in comparison.json.",
                      "Observed numerical shifts are descriptive, not statistical significance tests or proof of practical classification degradation. No external positive labels support such a conclusion."])
    else:
        lines.extend([f"Unavailable: {comparison['reason']}. Required file: {comparison['required_file']}."])
    lines.extend(["", "## Highest scores: manual review cases", ""])
    for case in result["extreme_cases"]:
        lines.extend([f"### {case['player_id']} in {case['match_id']}", "",
                      f"Score {case['score']}; {case['window_count']} windows; peer mean {case['peer_mean_score']}; completed-round coverage {case['completed_round_coverage']:.3%}; crossing windows {case['cross_round_window_count']}; unscored shots {case['unscored_shot_count']}.",
                      "| Feature | Median | P99 | Max |", "|---|---:|---:|---:|"])
        for feature, stats in case["feature_summary"].items():
            lines.append(f"| {feature} | {stats['median']} | {stats['p99']} | {stats['max']} |")
        lines.extend(["", f"RF signed path contributions: {json.dumps(case['model_contributions'], ensure_ascii=False)}.", case["interpretation"], ""])
    lines.extend(["## Figures", ""])
    lines.extend(f"![{name}]({name})\n" for name in result["figures"])
    lines.extend(["## Scientific limitations", ""])
    lines.extend(f"- {item}" for item in LIMITATIONS)
    lines.extend(["", "## Conclusion", "",
                  "Technical completion is recorded separately from scientific evidence. Successful processing supports pipeline usability for the included sources; score stability and flags describe only this sample.",
                  "User-declared labels, few matches and repeated players limit negative-class inference. Distribution differences are descriptive. Detection of cheaters, external calibration and generalization remain unvalidated.",
                  "Model/metadata integrity is checked after every demo and at completion; no model training or data download occurs.",
                  f"Reproducibility verification: {json.dumps(result['reproducibility'])}.", ""])
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


def analyze_cached(demo: Path, model: Path, output: Path, fingerprint: dict) -> tuple[dict, Path, bool]:
    """Content-addressed attempts preserve old/invalid reports; only verified receipts resume."""
    directory = output / "matches" / digest_json(fingerprint)
    directory.mkdir(parents=True, exist_ok=True)
    attempts = sorted(directory.glob("attempt-*"))
    for attempt in reversed(attempts):
        try:
            receipt = json.loads((attempt / "receipt.json").read_text(encoding="utf-8"))
            if receipt["fingerprint"] != fingerprint or receipt["report_sha256"] != sha256(attempt / "report.json") or not (attempt / "report.md").is_file():
                continue
            report = json.loads((attempt / "report.json").read_text(encoding="utf-8"))
            validate_report(report, demo)
            return report, attempt, True
        except (OSError, ValueError, KeyError, TypeError):
            continue
    attempt = directory / f"attempt-{len(attempts) + 1:04d}"
    attempt.mkdir()
    report = analyze_demo(demo, model, attempt, review_plots=False)
    validate_report(report, demo)
    write_json(attempt / "receipt.json", {"fingerprint": fingerprint, "report_sha256": sha256(attempt / "report.json")})
    return report, attempt, False


def historical_overlap(players: pd.DataFrame, root: Path, historical: list[Path]) -> dict:
    matches, identities, available = set(), set(), []
    for path in sorted((root / "demo_analyzer/data/processed/m6_robustness_20261014/after").glob("*/report.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        matches.add(report["match"]["match_id"])
        identities.update(p["player_id"] for p in report["players"])
        available.append(str(path.resolve()))
    matches.update(p.stem for p in historical)
    return {"match_ids": sorted({Path(m).stem for m in players.match_id} & matches), "player_ids": sorted(set(players.player_id) & identities),
            "historical_reports_checked": available, "identity_check_available": bool(available),
            "session_overlap": "Unknown: M6 exposes filename-derived match IDs, not independently verified session IDs"}


def run_evaluation(directory: Path, model_path: Path, output: Path, *, root: Path, manifest: Path | None = None,
                   reference: Path | None = None, seed: int = 42, draws: int = 5000) -> Path:
    directory, model_path, output, root = map(lambda p: Path(p).resolve(), (directory, model_path, output, root))
    if draws < 100 or seed < 0:
        raise ValueError("At least 100 bootstrap draws and a nonnegative seed required")
    if directory == output or directory in output.parents or output in directory.parents:
        raise ValueError("Input/output directories must be separate")
    training = root / "demo_analyzer/data/raw/train_sources"
    if directory == training or training in directory.parents:
        raise ValueError("External evaluation cannot use the training source directory")
    raw = root / "demo_analyzer/data/raw"
    if output == raw or raw in output.parents:
        raise ValueError("Evaluation outputs cannot be written into raw source directories")
    demos, rejected = discover_demos(directory)
    labels = load_labels(manifest, demos, directory)
    load_analysis_model(model_path)
    historical = sorted(training.rglob("*.dem"))
    audit = independence_audit(demos, historical)
    protocol = freeze_protocol(root, model_path, labels, audit, reference, seed=seed, draws=draws)
    # Dirty documentation and unrelated Git changes do not invalidate a frozen code/data run.
    run_key = digest_json({k: v for k, v in protocol.items() if k not in {"git_status", "git_head"}})
    run = output / f"run-{run_key[:16]}"
    run.mkdir(parents=True, exist_ok=True)
    if not (run / "protocol.json").exists():
        write_json(run / "protocol.json", protocol)
        with zipfile.ZipFile(run / "source_snapshot.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in protocol["source_hashes"]:
                archive.write(root / name, arcname=name)
    else:
        protocol = json.loads((run / "protocol.json").read_text(encoding="utf-8"))
    def check_integrity():
        if sha256(model_path) != protocol["model_sha256"] or sha256(model_path.with_suffix(".json")) != protocol["metadata_sha256"]:
            raise RuntimeError("Frozen model bundle changed during evaluation")
    historical_hashes = {s["sha256"] for s in audit["sources"] if s["population"] == "historical_technical"}
    seen, inventory, reports, player_rows, window_rows = set(), [], [], [], []
    analysis_hashes = {k: v for k, v in protocol["source_hashes"].items() if k.startswith("demo_analyzer/src/") and not k.endswith("/validation.py")}
    for demo in demos:
        source = next(s for s in audit["sources"] if s["path"] == str(demo))
        item = {**source, "match_id": demo.relative_to(directory).as_posix(), "status": "error"}
        if source["sha256"] in seen or source["sha256"] in historical_hashes:
            item.update(status="excluded_duplicate", reason="Exact duplicate of historical or earlier external demo")
        else:
            seen.add(source["sha256"])
            fingerprint = {"demo_path": str(demo), "demo_sha256": source["sha256"],
                           "model_sha256": protocol["model_sha256"], "metadata_sha256": protocol["metadata_sha256"],
                           "analysis_code_sha256": digest_json(analysis_hashes), "dependencies": protocol["dependencies"],
                           "python": protocol["python"], "window_size": WINDOW_SIZE, "tick_rate": TICK_RATE, "review_plots": False}
            try:
                report, path, reused = analyze_cached(demo, model_path, output, fingerprint)
                p, w = report_tables(report, labels.get(demo.relative_to(directory).as_posix(), {}))
                # Relative source path disambiguates equal stems in separate directories.
                for row in p + w:
                    row["match_id"] = item["match_id"]
                report["match"]["match_id"] = item["match_id"]
                reports.append(report)
                player_rows.extend(p)
                window_rows.extend(w)
                item.update(**report["summary"], map_name=report["match"].get("map_name"),
                            report_path=str(path), cache_reused=reused,
                            detected_player_ids=[p["player_id"] for p in report["players"]])
                print(f"{demo.name}: {item['status']}; {item['scored_player_count']}/{item['player_count']} players; {item['window_count']} windows; cached={reused}", flush=True)
            except Exception as error:
                item.update(status="error", reason=f"{type(error).__name__}: {error}")
                print(f"{demo.name}: ERROR {item['reason']}", flush=True)
        inventory.append(item)
        write_json(run / "inventory.json", inventory)
        check_integrity()
        if sha256(demo) != source["sha256"]:
            raise RuntimeError(f"Demo source changed during evaluation: {demo}")
    players = pd.DataFrame(player_rows, columns=PLAYER_COLUMNS)
    windows = pd.DataFrame(window_rows, columns=WINDOW_COLUMNS)
    players["score"] = pd.to_numeric(players.score, errors="coerce")
    windows["score"] = pd.to_numeric(windows.score, errors="coerce")
    summary = summarize(players, windows, inventory, seed=seed, draws=draws)
    comparison = reference_comparison(reference, model_path, windows, players, run)
    if comparison["status"] == "available" and comparison["source_sha256"] != protocol["reference"]["sha256"]:
        raise RuntimeError("CS2CD reference changed during evaluation")
    reproducibility = verify_saved_scores(model_path, windows, reports)
    overlap = historical_overlap(players, root, historical)
    extremes = extreme_cases(players, windows, reports)
    figures = plot_evaluation(players, summary, comparison, run)
    result = {"protocol": protocol, "statistics": summary, "inventory": inventory, "rejected_inputs": rejected,
              "historical_overlap": overlap, "comparison": comparison, "extreme_cases": extremes, "figures": figures,
              "limitations": LIMITATIONS, "model_integrity_verified": True, "reproducibility": reproducibility}
    check_integrity()
    for name, value in [("statistics.json", summary), ("comparison.json", comparison), ("evaluation.json", result)]:
        write_json(run / name, value)
    players.to_csv(run / "player_matches.csv", index=False)
    windows.to_csv(run / "windows.csv", index=False)
    pd.DataFrame(inventory).to_csv(run / "inventory.csv", index=False)
    pd.DataFrame([{k: v for k, v in r.items() if k != "by_match"} for r in summary["flag_rates"]]).to_csv(run / "thresholds.csv", index=False)
    pd.DataFrame([{"threshold": r["threshold"], **m} for r in summary["flag_rates"] for m in r["by_match"]]).to_csv(run / "threshold_by_match.csv", index=False)
    pd.DataFrame(summary["repeated_players"]).to_csv(run / "repeated_players.csv", index=False)
    markdown_report(result, run)
    write_json(output / "latest.json", {"run_directory": str(run), "counts": summary["counts"]})
    return run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("demo_analyzer/data/raw/held_out/legitimate"))
    parser.add_argument("--model", type=Path, default=Path("demo_analyzer/models/supervised/random_forest_v1.joblib"))
    parser.add_argument("--output", type=Path, default=Path("demo_analyzer/data/processed/validation_legitimate"))
    parser.add_argument("--manifest", type=Path, help="Optional JSON label/provenance overrides; see load_labels docstring")
    parser.add_argument("--reference", type=Path, default=Path("demo_analyzer/data/processed/supervised_dataset.csv"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap-draws", type=int, default=5000)
    args = parser.parse_args(argv)
    try:
        run = run_evaluation(args.input, args.model, args.output, root=Path.cwd(), manifest=args.manifest,
                             reference=args.reference, seed=args.seed, draws=args.bootstrap_draws)
        result = json.loads((run / "evaluation.json").read_text(encoding="utf-8"))
        print(f"Report: {run / 'report.md'}", flush=True)
        return 0 if result["statistics"]["counts"]["player_matches_scored"] and not result["statistics"]["counts"]["demos_excluded_or_failed"] else 2
    except Exception as error:
        print(f"Evaluation failed: {type(error).__name__}: {error}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
