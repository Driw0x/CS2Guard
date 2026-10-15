"""Reproduce M5 with its frozen model, then evaluate unused CS2CD matches.

Run from the repository root. Existing studies and datasets are never replaced.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import zipfile

import numpy as np
import pandas as pd

from cs2guard_demo.analysis import load_analysis_model, TICK_RATE, WINDOW_SIZE
from cs2guard_demo.cs2cd_validation import classification_summary, cluster_bootstrap, rank_players
from cs2guard_demo.dataset import DatasetBuilder
from cs2guard_demo.dataset.adapters import CS2CDAdapter
from cs2guard_demo.dataset.schema import AIM_FEATURE_COLUMNS, IDENTITY_COLUMNS, build_player_id
from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS, prepare_features
from cs2guard_demo.supervised import aggregate_player_scores, split_labeled_dataset
from cs2guard_demo.validation import THRESHOLDS, digest_json, sha256, write_json


def audit_sources(raw: Path, train: pd.DataFrame, test: pd.DataFrame) -> tuple[list[dict], pd.DataFrame]:
    """Use adapter identities, never directory names, to identify historical data."""
    training, testing = set(train.match_id), set(test.match_id)
    if training & testing:
        raise ValueError("Training/evaluation match overlap")
    inventory, rosters = [], []
    for path in sorted(raw.rglob("*.json")):
        if "cs2cd" not in path.parts:
            continue
        parquet = path.with_suffix(".parquet")
        adapter = CS2CDAdapter(path, parquet)
        match = adapter.match_id
        partition = "training" if match in training else "historical_test" if match in testing else "unused_negative" if not adapter.cheaters else "unused_positive"
        inventory.append({"match_id": match, "partition": partition,
                          "json_path": path.as_posix(), "parquet_path": parquet.as_posix(),
                          "json_sha256": sha256(path), "json_bytes": path.stat().st_size,
                          "parquet_bytes": parquet.stat().st_size,
                          "map_name": adapter.get_metadata().get("map_name"),
                          "annotated_suspects": len(adapter.cheaters)})
        rosters.append(adapter.get_labels())
    ids = [item["match_id"] for item in inventory]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate raw match IDs; resolve provenance before evaluation")
    if (training | testing) - set(ids):
        raise ValueError("Historical match sources absent from raw inventory")
    return inventory, pd.concat(rosters, ignore_index=True)


def extract_match(item: dict, cache: Path) -> tuple[str, pd.DataFrame, dict]:
    """Cache only new canonical features; each process handles one match at a time."""
    import pyarrow.parquet as parquet

    source, telemetry = Path(item["json_path"]), Path(item["parquet_path"])
    fingerprint = {"json_sha256": sha256(source), "parquet_sha256": sha256(telemetry)}
    if fingerprint["json_sha256"] != item["json_sha256"]:
        raise ValueError("Source JSON changed after audit")
    directory = cache / item["match_id"]
    directory.mkdir(parents=True, exist_ok=True)
    csv, receipt = directory / "features.csv", directory / "receipt.json"
    if receipt.exists():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        if saved["inputs"] != fingerprint or sha256(csv) != saved["features_sha256"]:
            raise ValueError("Canonical feature cache integrity failure")
        return item["match_id"], pd.read_csv(csv, dtype={c: str for c in IDENTITY_COLUMNS}), saved
    if csv.exists():
        raise ValueError("Incomplete feature cache; preserve it and use a new output directory")
    adapter = CS2CDAdapter(source, telemetry)
    raw_rows = parquet.ParquetFile(telemetry).metadata.num_rows
    ticks, events = adapter.get_ticks(), adapter.get_events()
    builder = DatasetBuilder()
    windows = builder.build_canonical_temporal_windows(ticks, events, window_size=WINDOW_SIZE)
    features = builder.build_aim_features(windows, tick_rate=TICK_RATE)
    if features.empty:
        features = pd.DataFrame(columns=AIM_FEATURE_COLUMNS)
    prepare_features(features)
    features.to_csv(csv, index=False)
    saved = {"inputs": fingerprint, "features_sha256": sha256(csv),
             "raw_tick_rows": raw_rows, "retained_tick_rows": len(ticks),
             "discarded_invalid_tick_rows": raw_rows - len(ticks), "canonical_events": len(events),
             "unique_shot_events": int(events.loc[events.event_type.eq("shot")].drop_duplicates(["match_id", "player_id", "tick"]).shape[0]),
             "windows": len(features), "window_tick_rows": len(windows)}
    write_json(receipt, saved)
    # Evaluate exactly the persisted rows, both during the first run and on resume.
    return item["match_id"], pd.read_csv(csv, dtype={c: str for c in IDENTITY_COLUMNS}), saved


def score_features(features: pd.DataFrame, model, reloaded_model) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    if features[IDENTITY_COLUMNS + ["window_id", "shot_tick"]].isna().any().any():
        raise ValueError("Missing canonical identity/window values")
    if features.window_id.duplicated().any():
        raise ValueError("Duplicate windows")
    expected = [build_player_id(r.source, r.match_id, r.source_player_id, r.identity_scope)
                for r in features[IDENTITY_COLUMNS].drop_duplicates().itertuples(index=False)]
    if expected != features[IDENTITY_COLUMNS].drop_duplicates().player_id.tolist():
        raise ValueError("Canonical player identity mismatch")
    X = prepare_features(features)
    scores = model.predict_proba(X)[:, list(model.classes_).index(1)]
    repeated = reloaded_model.predict_proba(X)[:, list(reloaded_model.classes_).index(1)]
    if repeated.shape != scores.shape or not np.isfinite(repeated).all():
        raise ValueError("Invalid repeated inference")
    delta = float(np.max(np.abs(scores - repeated)))
    if not np.isfinite(scores).all() or not np.logical_and(scores >= 0, scores <= 1).all() or delta > 1e-12:
        raise ValueError("Invalid or non-reproducible inference")
    players = aggregate_player_scores(features, scores, "score")
    windows = features.copy()
    windows["score"] = scores
    counts = windows.groupby(["match_id", "player_id"]).size().rename("window_count")
    players = players.merge(counts, on=["match_id", "player_id"], validate="one_to_one")
    independent = windows.groupby(["match_id", "player_id"]).score.apply(lambda x: np.mean(x.to_numpy()))
    aggregated = players.set_index(["match_id", "player_id"]).score
    if not np.allclose(independent.loc[aggregated.index], aggregated, rtol=0, atol=1e-12):
        raise ValueError("Window/player aggregation mismatch")
    return rank_players(players), windows, delta


def save_population(name: str, players: pd.DataFrame, output: Path, roster: pd.DataFrame, *, seed: int, draws: int, match_ids=None) -> dict:
    players = rank_players(players)
    players.to_csv(output / f"{name}_player_scores.csv", index=False)
    evaluated_ids = set(players.match_id) if match_ids is None else set(match_ids)
    if set(players.match_id) - evaluated_ids:
        raise ValueError("Scored matches outside the evaluation population")
    labels = roster[roster.match_id.isin(evaluated_ids)]
    coverage = labels.merge(players[["match_id", "player_id", "label", "score"]], on=["match_id", "player_id"], how="outer", validate="one_to_one", suffixes=("", "_scored"), indicator=True)
    if coverage._merge.eq("right_only").any() or not coverage.loc[coverage._merge.eq("both"), "label"].eq(coverage.loc[coverage._merge.eq("both"), "label_scored"]).all():
        raise ValueError("Scored player identities/labels disagree with raw CS2CD roster")
    coverage = coverage.drop(columns=["_merge", "label_scored"])
    coverage.to_csv(output / f"{name}_roster.csv", index=False)
    result = {"metrics": classification_summary(players), "bootstrap": cluster_bootstrap(players, seed=seed, draws=draws),
              "processed_matches": len(evaluated_ids), "matches_without_scores": sorted(evaluated_ids - set(players.match_id)),
              "roster_player_matches": len(coverage), "unscored_player_matches": int(coverage.score.isna().sum())}
    by_match = []
    for match, rows in players.groupby("match_id", sort=True):
        by_match.append({"match_id": match, **classification_summary(rows), "mean_score": float(rows.score.mean()),
                         "min_score": float(rows.score.min()), "max_score": float(rows.score.max())})
    write_json(output / f"{name}_by_match.json", by_match)
    errors = pd.concat([players[players.label.eq("suspicious")].nsmallest(10, "score").assign(case="low_score_suspicious"),
                        players[players.label.eq("legitimate")].nlargest(10, "score").assign(case="high_score_legitimate")])
    errors.to_csv(output / f"{name}_error_cases.csv", index=False)
    result["error_examples"] = errors.head(5).to_dict(orient="records") if name == "unused_negative" else pd.concat([errors[errors.case.eq("low_score_suspicious")].head(5), errors[errors.case.eq("high_score_legitimate")].head(5)]).to_dict(orient="records")
    result["match_mean_score_range"] = [min(row["mean_score"] for row in by_match), max(row["mean_score"] for row in by_match)]
    write_json(output / f"{name}_metrics.json", result)
    return result


def write_report(output: Path, protocol: dict, populations: dict, integrity: dict) -> None:
    lines = ["# M6 — Frozen CS2CD evaluation (2026-10-15)", "",
             "The historical test is a reproduction, already used for M5 evaluation and descriptive thresholds. "
             "The unused cohort is absent from the inspected development artifacts; this is not proof it was never viewed.", "",
             "The existing labeled CSV supplies historical features. New matches use the unchanged CS2CD JSON/Parquet adapter and canonical builder. "
             "No native .dem parsing is evaluated. No fitting, calibration or threshold selection occurs.", "",
             f"Model SHA-256: `{protocol['contract']['model_sha256']}`. Metadata: `{protocol['contract']['metadata_sha256']}`.", "",
             "Scores are arithmetic means of uncalibrated class-1 outputs per player-match. Ranking: descending score, ascending canonical player ID on ties. "
             "All player-matches receive equal metric weight. AP is sklearn average_precision_score, not trapezoidal PR area.", "",
             f"95% percentile intervals resample whole matches with replacement ({protocol['contract']['bootstrap_draws']} draws, seed {protocol['contract']['bootstrap_seed']}). "
             "They condition on this frozen model and match independence. Anonymous Player_N IDs remain scoped to matches; "
             "persistent real-player dependence cannot be identified or corrected. Windows are never independent resampling observations.", ""]
    for name, result in populations.items():
        metrics, ci = result["metrics"], result["bootstrap"]
        lines.extend([f"## {name}", "", f"Counts: `{json.dumps(metrics['counts'], sort_keys=True)}`.", "",
                      f"Processed matches: {result['processed_matches']}; matches without scored players: {result['matches_without_scores']}.", "",
                      f"Roster: {result['roster_player_matches']} player-matches, {result['unscored_player_matches']} without features (excluded from score denominators).", "",
                      f"ROC-AUC: {metrics['discrimination']['roc_auc']}; AP: {metrics['discrimination']['pr_auc']}; "
                      f"Hit@1: {metrics['hit_at_1']}; Hit@3: {metrics['hit_at_3']}.", "",
                      f"95% intervals: `{json.dumps({k: ci[k] for k in ['discrimination', 'hit_at_1', 'hit_at_3']}, sort_keys=True)}`.", "",
                      "Hit@k counts matches with at least one labeled suspect among the first k scored players, among matches with scored suspects only.", "",
                      "| Threshold (>=) | Precision | Recall | F1 | FPR | TN | FP | FN | TP |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"])
        for row in metrics["thresholds"]:
            lines.append("| " + " | ".join(str(row[k]) for k in ["threshold", "precision", "recall", "f1", "false_positive_rate", "tn", "fp", "fn", "tp"]) + " |")
        lines.extend(["", f"Full threshold confidence intervals: `{name}_metrics.json`. Exact identities, labels, ranks and window counts: `{name}_player_scores.csv`. "
                      f"Match differences: `{name}_by_match.json`; ten low-score labeled suspects and ten high-score labeled legitimate cases: `{name}_error_cases.csv`.", ""])
        lines.extend([f"Match mean score range: {result['match_mean_score_range']}.", "",
                      "| Error case | Match | Anonymous player | Score | Windows | Rank |", "|---|---|---|---:|---:|---:|"])
        for row in result["error_examples"]:
            lines.append(f"| {row['case']} | {row['match_id']} | {row['player_id']} | {row['score']:.8f} | {row['window_count']} | {row['rank']} |")
        lines.append("")
    lines.extend(["## Historical comparison and integrity", "", f"`{json.dumps(integrity, sort_keys=True)}`", "",
                  "The historical model metadata is the full-precision reference (ROC-AUC 0.7778977453159733; AP 0.6839833414991215). "
                  "The same source population, split, model bytes, six ordered inputs and arithmetic mean define this comparison. "
                  "Agreement verifies the historical experiment; it is not an independent estimate of generalization.", "",
                  "## Limits and evidence", "",
                  "The unused cohort has only negative CS2CD annotations. Its discrimination, recall and Hit@k cannot be estimated. "
                  "Pooling it into the historical test would alter prevalence and is not done. Missing cheater annotations are treated as legitimate by the existing adapter; "
                  "CS2CD labels are not perfect ground truth. New-cohort false-positive rates are conditional on those annotations.", "",
                  "The fixed 0.10–0.90 grid is descriptive; no best or operational threshold is selected. Precision with no predicted positives is zero by sklearn convention. "
                  "Undefined recall/F1/FPR and ranking metrics are null. Degenerate bootstrap intervals do not bound population risk. "
                  "Scored-player coverage does not establish unbiased coverage of unscored players.", "",
                  "Historical feature checks apply to retained cached rows, not raw rows discarded during their original extraction. "
                  "New-match receipts record raw/retained tick counts and canonical window coverage. "
                  "This study does not establish calibrated cheating probabilities, native-demo detection performance or real-player independence.", "",
                  "`protocol.json` freezes the historical CSV, JSON inventory, code, environment and configuration before inference; "
                  "each extraction receipt hashes its Parquet input before scoring. `sources.zip` preserves executed source. "
                  "`partitions.json`, `raw_inventory.csv`, `raw_roster.csv`, per-match receipts, window scores and player scores identify the evaluated data. "
                  "Resume repeats inference and metrics using hash-checked canonical feature caches. Existing historical studies are not overwritten.", "",
                  "Reproduce from the repository root: `.\\.venv\\Scripts\\python.exe demo_analyzer/scripts/evaluate_cs2cd.py`. "
                  "Use a different `--output` directory for a fresh complete extraction.", ""])
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("demo_analyzer/data/processed/supervised_dataset.csv"))
    parser.add_argument("--raw", type=Path, default=Path("demo_analyzer/data/raw"))
    parser.add_argument("--model", type=Path, default=Path("demo_analyzer/models/supervised/random_forest_v1.joblib"))
    parser.add_argument("--output", type=Path, default=Path("demo_analyzer/data/processed/validation_cs2cd_20261015"))
    parser.add_argument("--bootstrap-draws", type=int, default=5000)
    parser.add_argument("--workers", type=int, default=2, help="Canonical extraction processes; scoring remains in the parent process.")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be at least one")
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    model, metadata = load_analysis_model(args.model)
    reloaded_model, _ = load_analysis_model(args.model)
    data = pd.read_csv(args.dataset, dtype={c: str for c in IDENTITY_COLUMNS})
    if set(data.source) != {"cs2cd"} or not data.identity_scope.eq("match").all():
        raise ValueError("Historical M5 dataset must contain match-scoped CS2CD rows only")
    prepare_features(data)
    if data[IDENTITY_COLUMNS + ["window_id", "shot_tick"]].isna().any().any() or data.window_id.duplicated().any():
        raise ValueError("Invalid historical identities or duplicate windows")
    train, test = split_labeled_dataset(data, test_size=.2, random_state=42)
    for split, rows in [("training", train), ("test", test)]:
        if metadata[split]["samples"] != len(rows) or metadata[split]["matches"] != rows.match_id.nunique():
            raise ValueError("Current dataset does not reproduce persisted M5 split counts")
    inventory, roster = audit_sources(args.raw, train, test)
    new = [item for item in inventory if item["partition"].startswith("unused")]
    if any(item["partition"] == "unused_positive" for item in new):
        raise ValueError("Unused positive matches require a separate cohort interpretation")
    sources = sorted([*Path("demo_analyzer/src").rglob("*.py"), Path("demo_analyzer/scripts/evaluate_cs2cd.py"), Path("pyproject.toml")])
    source_hashes = {p.as_posix(): sha256(p) for p in sources}
    contract = {"model_sha256": sha256(args.model), "metadata_sha256": sha256(args.model.with_suffix(".json")),
                "dataset_sha256": sha256(args.dataset), "source_hashes": source_hashes,
                "raw_inventory_sha256": digest_json(inventory), "features": FEATURE_COLUMNS,
                "window_size": WINDOW_SIZE, "tick_rate": TICK_RATE, "test_size": .2, "split_seed": 42,
                "bootstrap_seed": 42, "bootstrap_draws": args.bootstrap_draws, "thresholds": list(THRESHOLDS)}
    protocol = {"contract": contract, "model_metadata": metadata, "python": platform.python_version(),
                "dependencies": {name: version(name) for name in ["numpy", "pandas", "scikit-learn", "joblib", "pyarrow", "demoparser2"]},
                "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                "git_status": subprocess.check_output(["git", "status", "--short"], text=True),
                "extraction_workers": args.workers, "aggregation": "arithmetic mean per player-match", "ranking": "score descending; player_id ascending"}
    frozen = output / "protocol.json"
    if frozen.exists():
        if json.loads(frozen.read_text(encoding="utf-8"))["contract"] != contract:
            raise ValueError("Study contract changed; preserve this study and choose a new --output")
    else:
        write_json(frozen, protocol)
        with zipfile.ZipFile(output / "sources.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for path, expected in source_hashes.items():
                if sha256(Path(path)) != expected:
                    raise ValueError("Source changed during protocol freeze")
                archive.write(path, arcname=path)
    pd.DataFrame(inventory).to_csv(output / "raw_inventory.csv", index=False)
    roster.to_csv(output / "raw_roster.csv", index=False)
    write_json(output / "partitions.json", {"training": sorted(train.match_id.unique()), "historical_test": sorted(test.match_id.unique()),
                                           "unused_negative": sorted(item["match_id"] for item in new),
                                           "training_evaluation_overlap": []})
    expected = roster.merge(data[IDENTITY_COLUMNS].drop_duplicates(), on=["match_id", "player_id"], suffixes=("_raw", "_cached"))
    if len(expected) != data[["match_id", "player_id"]].drop_duplicates().shape[0] or not expected.label_raw.eq(expected.label_cached).all():
        raise ValueError("Historical cached identities/labels disagree with raw CS2CD")
    players, windows, delta = score_features(test, model, reloaded_model)
    if len(players) != metadata["test"]["player_matches"]:
        raise ValueError("Historical scored player count mismatch")
    windows.to_csv(output / "historical_test_window_scores.csv", index=False)
    populations = {"historical_test": save_population("historical_test", players, output, roster, seed=42, draws=args.bootstrap_draws)}
    comparison = {key: populations["historical_test"]["metrics"]["discrimination"][key] - value for key, value in metadata["metrics"]["player"].items()}
    if any(abs(value) > 1e-12 for value in comparison.values()):
        raise ValueError("Frozen model does not reproduce historical player metrics")
    write_report(output, protocol, populations, {"historical_metric_deltas": comparison, "repeat_max_window_delta": delta, "new_cohort_status": "running"})
    print(json.dumps({"historical": populations["historical_test"]["metrics"], "new_matches": len(new)}), flush=True)
    all_players, receipts = [], []
    cache = output / "canonical_cache"
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        # Workers return only small feature tables, never the raw telemetry frames.
        for match, features, receipt in pool.map(extract_match, new, [cache] * len(new)):
            if features.empty:
                w = features.assign(score=pd.Series(dtype=float))
            else:
                p, w, difference = score_features(features, model, reloaded_model)
                delta = max(delta, difference)
                all_players.append(p)
            w.to_csv(cache / match / "window_scores.csv", index=False)
            receipts.append({"match_id": match, **receipt})
            print(f"{len(receipts)}/{len(new)} {match}: {features.player_id.nunique()} players, {len(w)} windows", flush=True)
    if all_players:
        populations["unused_negative"] = save_population("unused_negative", pd.concat(all_players, ignore_index=True), output, roster, seed=42, draws=args.bootstrap_draws, match_ids=[item["match_id"] for item in new])
    write_json(output / "extraction_integrity.json", receipts)
    if contract["model_sha256"] != sha256(args.model) or contract["metadata_sha256"] != sha256(args.model.with_suffix(".json")) or contract["dataset_sha256"] != sha256(args.dataset):
        raise ValueError("Frozen model, metadata or historical dataset changed")
    integrity = {"historical_metric_deltas": comparison, "repeat_max_window_delta": delta,
                 "training_evaluation_overlap": [], "new_cohort_status": "complete", "new_matches": len(receipts),
                 "new_scored_matches": sum(r["windows"] > 0 for r in receipts),
                 "new_windows": sum(r["windows"] for r in receipts), "invalid_new_tick_rows_discarded": sum(r["discarded_invalid_tick_rows"] for r in receipts),
                 "model_metadata_dataset_unchanged": True}
    write_json(output / "integrity.json", integrity)
    write_report(output, protocol, populations, integrity)
    print(json.dumps({"output": output.as_posix(), "integrity": integrity}), flush=True)


if __name__ == "__main__":
    main()
