"""Offline demo inference using the M2/M3 features and a persisted M5 model."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier

from cs2guard_demo.dataset import DatasetBuilder
from cs2guard_demo.dataset.adapters import DemoAdapter
from cs2guard_demo.dataset.schema import build_player_id
from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS, prepare_features
from cs2guard_demo.features import (
    angular_distance, count_aim_corrections, crosshair_to_target_distance,
    find_potential_overshoots, mean_tracking_error, tracking_time_on_target_ratio,
)
from cs2guard_demo.supervised import LABEL_TO_TARGET, aggregate_player_scores, load_model_bundle
from cs2guard_demo.visualization import plot_aim_trajectory

WINDOW_SIZE = 32
TICK_RATE = 64.0
REVIEW_WINDOWS_PER_PLAYER = 3


def load_analysis_model(model_path: str | Path) -> tuple[object, dict]:
    """Validate the inference contract, without fitting or calibrating a model."""
    model_path = Path(model_path)
    metadata_path = model_path.with_suffix(".json")
    for path in (model_path, metadata_path):
        if not path.is_file():
            raise FileNotFoundError(f"Model bundle file not found: {path}")
    model, metadata = load_model_bundle(model_path, metadata_path)
    if not isinstance(metadata, dict):
        raise ValueError("Model metadata must be an object")
    if metadata.get("features") != FEATURE_COLUMNS:
        raise ValueError("Model metadata features must match the six M5 features in order")
    if metadata.get("label_mapping") != LABEL_TO_TARGET:
        raise ValueError("Model label mapping must be legitimate=0, suspicious=1")
    for key in ("model_name", "version"):
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"Model metadata requires {key}")
    if metadata.get("window_size", WINDOW_SIZE) != WINDOW_SIZE:
        raise ValueError("Model window_size must be 32")
    if metadata.get("tick_rate", TICK_RATE) != TICK_RATE:
        raise ValueError("Model tick_rate must be 64 Hz")
    if not callable(getattr(model, "predict_proba", None)):
        raise ValueError("Model must support predict_proba")
    if getattr(model, "n_features_in_", None) != len(FEATURE_COLUMNS):
        raise ValueError("Model input dimension must be six")
    names = getattr(model, "feature_names_in_", None)
    if names is not None and list(names) != FEATURE_COLUMNS:
        raise ValueError("Model feature names must match metadata in order")
    classes = np.asarray(getattr(model, "classes_", []))
    if classes.shape != (2,) or set(classes.tolist()) != {0, 1}:
        raise ValueError("Model classes must be numeric 0 and 1")
    return model, metadata


def _round_number(tick: int, rounds: list) -> int | None:
    return next((r.number for r in rounds if r.start_tick <= tick <= r.end_tick), None)


def _crosses_round_boundary(start_tick: int, end_tick: int, rounds: list) -> bool:
    return any(start_tick < r.start_tick <= end_tick or start_tick <= r.end_tick < end_tick
               for r in rounds)


def _player_id(steamid: int, match_id: str) -> str:
    return build_player_id("demo", match_id, str(steamid), "global")


def tree_probability_contributions(model, features: pd.DataFrame) -> tuple[float, np.ndarray] | None:
    """Decompose tree probabilities into root baseline and signed path changes.

    This telescoping decomposition explains the existing prediction. It depends
    on tree split order and is neither a causal attribution nor a SHAP value.
    """
    if isinstance(model, RandomForestClassifier):
        trees = model.estimators_
    elif isinstance(model, DecisionTreeClassifier):
        trees = [model]
    else:
        return None
    # sklearn tree inference compares float32 input against float64 thresholds.
    values = features.to_numpy(dtype=np.float32)
    class_index = list(model.classes_).index(1)
    contributions = np.zeros(values.shape, dtype=float)
    baseline = 0.0
    rows = np.arange(len(values))
    for estimator in trees:
        tree = estimator.tree_
        counts = tree.value[:, 0, :]
        probabilities = counts[:, class_index] / counts.sum(axis=1)
        baseline += probabilities[0]
        nodes = np.zeros(len(values), dtype=int)
        active = tree.children_left[nodes] != tree.children_right[nodes]
        while active.any():
            indices, parents = rows[active], nodes[active]
            columns = tree.feature[parents]
            children = np.where(values[indices, columns] <= tree.threshold[parents],
                                tree.children_left[parents], tree.children_right[parents])
            contributions[indices, columns] += probabilities[children] - probabilities[parents]
            nodes[indices] = children
            active = tree.children_left[nodes] != tree.children_right[nodes]
    return float(baseline / len(trees)), contributions / len(trees)


def _plot_review_window(window, ticks, events, output_dir):
    """Use observed victim geometry, or explicitly label a shot-direction reference."""
    samples = ticks[(ticks["player_id"] == window["player_id"]) &
                    ticks["tick"].between(window["start_tick"], window["end_tick"])].sort_values("tick")
    contacts = [e for e in events if e["event_type"] in {"hit", "kill"} and e.get("victim_id")]
    contacts.sort(key=lambda e: (abs(e["tick"] - window["shot_tick"]), e["event_id"]))
    distances = []
    sample_ticks = []
    reference = "shot_aim_direction"
    target_id = None
    if contacts:
        target_id = contacts[0]["victim_id"]
        target_ticks = ticks[ticks["player_id"] == target_id].drop_duplicates("tick", keep=False).set_index("tick")
        for row in samples.itertuples(index=False):
            if row.tick not in target_ticks.index:
                continue
            target = target_ticks.loc[row.tick]
            distances.append(crosshair_to_target_distance(
                (row.x, row.y, row.z), row.yaw, row.pitch,
                (target["x"], target["y"], target["z"]),
            ))
            sample_ticks.append(int(row.tick))
        if len(sample_ticks) >= 2:
            reference = "observed_victim_position"
    if reference == "shot_aim_direction":
        sample_ticks = samples["tick"].astype(int).tolist()
        last = samples.iloc[-1]
        distances = [angular_distance(r.yaw, r.pitch, last["yaw"], last["pitch"])
                     for r in samples.itertuples(index=False)]
    if not np.isfinite(distances).all():
        return {"path": None, "reason": "Non-finite aim geometry", "reference": reference}
    overshoots = find_potential_overshoots(distances) if reference == "observed_victim_position" else []
    filename = f"aim_{window['source_player_id']}_{window['shot_tick']}.png"
    path = output_dir / filename
    plot_aim_trajectory(
        sample_ticks, distances, shot_ticks=[window["shot_tick"]],
        hit_ticks=[e["tick"] for e in contacts if e["event_type"] == "hit"],
        overshoot_ticks=[sample_ticks[i] for i in overshoots],
        title=f"{window['player_id']} | round {window['round_number']} | shot {window['shot_tick']}",
        show=False, output_path=path,
        distance_label=("Crosshair-to-target distance" if reference == "observed_victim_position"
                        else "Distance to shot aim direction"),
    )
    result = {"path": filename, "reference": reference, "target_id": target_id,
              "sample_count": len(sample_ticks), "start_tick": sample_ticks[0],
              "end_tick": sample_ticks[-1]}
    if reference == "observed_victim_position":
        result["tracking"] = {
            "mean_error_degrees": mean_tracking_error(distances),
            "on_target_ratio": tracking_time_on_target_ratio(distances),
            "threshold_degrees": 3.0,
            "corrections": count_aim_corrections(distances),
            "potential_overshoot_ticks": [sample_ticks[i] for i in overshoots],
        }
    else:
        result["tracking"] = None
        result["tracking_unavailable_reason"] = (
            "Fewer than two concurrent samples for the linked victim" if contacts
            else "No hit or kill linked by attacker, weapon, round and the two-tick interval"
        )
    return result


def analyze_demo(demo_path: str | Path, model_path: str | Path, output_dir: str | Path,
                 *, review_plots: bool = True) -> dict:
    """Analyze all players, write JSON/Markdown and inspectable M2 aim plots."""
    demo_path, model_path, output_dir = Path(demo_path), Path(model_path), Path(output_dir)
    if not demo_path.is_file():
        raise FileNotFoundError(f"Demo file not found: {demo_path}")
    if demo_path.suffix.lower() != ".dem" or demo_path.stat().st_size == 0:
        raise ValueError("Input must be a non-empty .dem file")
    model, metadata = load_analysis_model(model_path)
    adapter = DemoAdapter(demo_path)
    ticks, events = adapter.get_ticks(), adapter.get_events()
    roster, rounds = adapter.parser.get_players(), adapter.parser.get_rounds()
    builder = DatasetBuilder()
    windows = builder.build_canonical_temporal_windows(ticks, events, window_size=WINDOW_SIZE)
    features = builder.build_aim_features(windows, tick_rate=TICK_RATE)

    players_by_id = {}
    for player in roster:
        if player.steamid > 0:
            pid = _player_id(player.steamid, adapter.match_id)
            players_by_id[pid] = {"player_id": pid, "source_player_id": str(player.steamid),
                                  "player_name": player.name if isinstance(player.name, str) else str(player.steamid)}
    for frame in (ticks, events):
        for row in frame.drop_duplicates("player_id").to_dict("records"):
            players_by_id.setdefault(row["player_id"], {
                "player_id": row["player_id"], "source_player_id": row["source_player_id"],
                "player_name": row.get("player_name") or row["source_player_id"],
            })
    event_records = []
    clean_events = events.astype(object).where(pd.notna(events), None)
    for index, row in enumerate(clean_events.to_dict("records")):
        row["event_id"] = f"event_{index + 1}"
        row["tick"] = int(row["tick"])
        row["round_number"] = _round_number(row["tick"], rounds)
        event_records.append(row)
        if pd.notna(row.get("victim_id")):
            players_by_id.setdefault(row["victim_id"], {
                "player_id": row["victim_id"], "source_player_id": row["victim_source_player_id"],
                "player_name": row.get("victim_name") or row["victim_source_player_id"],
            })

    scored_windows = []
    if not features.empty:
        inputs = prepare_features(features)
        probabilities = np.asarray(model.predict_proba(inputs))
        if probabilities.shape != (len(features), 2) or not np.isfinite(probabilities).all():
            raise ValueError("Model returned invalid probability dimensions or values")
        if (probabilities < 0).any() or (probabilities > 1).any() or not np.allclose(probabilities.sum(axis=1), 1):
            raise ValueError("Model returned invalid probabilities")
        scores = probabilities[:, list(model.classes_).index(1)]
        attribution = tree_probability_contributions(model, inputs)
        if attribution is not None and not np.allclose(attribution[0] + attribution[1].sum(axis=1), scores, rtol=1e-12, atol=1e-12):
            raise ValueError("Tree contributions do not reconstruct model probabilities")
        player_scores = aggregate_player_scores(features, scores, "score").set_index("player_id")["score"]
        windows_by_id = dict(tuple(windows.groupby("window_id", sort=False)))
        events_by_player = {}
        for event in event_records:
            events_by_player.setdefault(event["player_id"], []).append(event)
        for index, feature in enumerate(features.to_dict("records")):
            window = windows_by_id[feature["window_id"]]
            shot_tick = int(feature["shot_tick"])
            linked_events = [e for e in events_by_player.get(feature["player_id"], [])
                             if 0 <= e["tick"] - shot_tick <= 2 and
                             e["round_number"] == _round_number(shot_tick, rounds) and
                             (e.get("weapon") or "").removeprefix("weapon_") ==
                             (feature.get("weapon") or "").removeprefix("weapon_") and
                             (e["event_type"] != "shot" or e["tick"] == shot_tick)]
            start_tick, end_tick = int(window["tick"].min()), int(window["tick"].max())
            scored_windows.append({
                "window_id": feature["window_id"], "player_id": feature["player_id"],
                "source_player_id": feature["source_player_id"], "shot_tick": shot_tick,
                "start_tick": start_tick, "end_tick": end_tick, "tick_count": len(window),
                "round_number": _round_number(shot_tick, rounds),
                "crosses_round_boundary": _crosses_round_boundary(start_tick, end_tick, rounds),
                "weapon": feature.get("weapon"), "score": float(scores[index]),
                "features": {name: float(feature[name]) for name in FEATURE_COLUMNS},
                "events": linked_events,
                "model_contributions": None if attribution is None else {
                    "method": "tree_probability_path", "baseline": attribution[0],
                    "features": dict(zip(FEATURE_COLUMNS, map(float, attribution[1][index]))),
                    "score": float(scores[index]),
                    "interpretation": "Signed root-to-leaf probability changes, averaged over trees; baseline plus contributions equals score. Path-dependent, not causal or SHAP.",
                },
                "explanation": "Measured features are descriptive; global importance is not a local contribution or proof of cheating. Local tree-path contributions are reported separately when supported.",
            })
    else:
        player_scores = pd.Series(dtype=float)

    scored_windows.sort(key=lambda w: (w["player_id"], w["shot_tick"], w["window_id"]))
    windows_by_player = {}
    for window in scored_windows:
        windows_by_player.setdefault(window["player_id"], []).append(window)
    players = []
    review_events = []
    for pid, player in players_by_id.items():
        player_windows = windows_by_player.get(pid, [])
        shot_count = sum(e["player_id"] == pid and e["event_type"] == "shot" for e in event_records)
        tick_count = int(ticks["player_id"].eq(pid).sum())
        player.update({"tick_count": tick_count, "shot_count": shot_count,
                       "window_count": len(player_windows), "unscored_shot_count": max(0, shot_count - len(player_windows)),
                       "score": float(player_scores.loc[pid]) if player_windows else None,
                       "status": "scored" if player_windows else "insufficient_data",
                       "reason": None if player_windows else "No complete 32-tick shot window with finite aim features",
                       "behavioral_scores": {
                           "kind": "descriptive_indicators",
                           "angular_speed": {"value": float(np.mean([w["features"]["mean_angular_speed"] for w in player_windows])) if player_windows else None, "unit": "degrees/second"},
                           "angular_acceleration": {"value": float(np.mean([w["features"]["mean_angular_acceleration"] for w in player_windows])) if player_windows else None, "unit": "degrees/second^2"},
                           "tracking": {"value": None, "reason": "Available only for review sequences with an observed victim; see visualization.tracking"},
                           "reaction": {"value": None, "reason": "No observed visibility stimulus; reaction time cannot be inferred reliably"},
                       }})
        ordered = sorted(player_windows, key=lambda w: (-w["score"], w["shot_tick"], w["window_id"]))
        player["model_contributions"] = None
        if player_windows and player_windows[0]["model_contributions"] is not None:
            player["model_contributions"] = {
                "method": "mean_tree_probability_path", "baseline": player_windows[0]["model_contributions"]["baseline"],
                "features": {name: float(np.mean([w["model_contributions"]["features"][name] for w in player_windows])) for name in FEATURE_COLUMNS},
                "score": player["score"],
                "interpretation": "Mean signed window contributions, matching M5 mean aggregation; path-dependent, not causal or SHAP.",
            }
        player["review_window_ids"] = [w["window_id"] for w in ordered[:REVIEW_WINDOWS_PER_PLAYER]]
        review_events.extend(ordered[:REVIEW_WINDOWS_PER_PLAYER])
        players.append(player)
    players.sort(key=lambda p: (p["score"] is None, -(p["score"] or 0), p["player_id"]))
    for rank, player in enumerate(players, 1):
        player["rank"] = rank if player["score"] is not None else None
    review_events.sort(key=lambda w: (-w["score"], w["player_id"], w["shot_tick"]))
    round_rows = []
    for r in rounds:
        entries = [w for w in scored_windows if w["round_number"] == r.number]
        round_rows.append({"number": r.number, "start_tick": r.start_tick, "end_tick": r.end_tick,
                           "winner": r.winner, "reason": r.reason, "window_count": len(entries),
                           "max_window_score": max((w["score"] for w in entries), default=None),
                           "review_window_ids": [w["window_id"] for w in review_events if w["round_number"] == r.number]})
    round_rows.sort(key=lambda r: (r["max_window_score"] is None, -(r["max_window_score"] or 0), r["number"]))
    scored_count = sum(p["status"] == "scored" for p in players)
    unscored_shot_count = sum(p["unscored_shot_count"] for p in players)
    missing_round_count = sum(w["round_number"] is None for w in scored_windows)
    boundary_count = sum(w["crosses_round_boundary"] for w in scored_windows)
    importance = getattr(model, "feature_importances_", None)
    report = {
        "match": {**adapter.get_metadata(), "demo_path": str(demo_path.resolve())},
        "model": {"path": str(model_path.resolve()), "model_name": metadata["model_name"],
                  "version": metadata["version"], "features": FEATURE_COLUMNS,
                  "decision_threshold": metadata.get("decision_threshold"), "threshold_applied": False,
                  "window_size": WINDOW_SIZE, "tick_rate": TICK_RATE,
                  "score_kind": "uncalibrated_supervised_class1_probability",
                  "player_aggregation": "Arithmetic mean of window scores, as evaluated in M5"},
        "summary": {"status": "insufficient_data" if not scored_count else ("complete" if scored_count == len(players) and not unscored_shot_count and not missing_round_count and not boundary_count else "partial"),
                    "player_count": len(players), "scored_player_count": scored_count,
                    "tick_count": len(ticks), "event_count": len(events), "window_count": len(scored_windows),
                    "round_count": len(rounds), "unscored_shot_count": unscored_shot_count,
                    "missing_round_window_count": missing_round_count, "cross_round_window_count": boundary_count},
        "players": players, "windows": scored_windows, "rounds": round_rows,
        "review_events": review_events,
        "feature_importance": {"kind": "global_model_importance_not_local_attribution",
                               "values": dict(zip(FEATURE_COLUMNS, map(float, importance))) if importance is not None else None},
        "limitations": [
            "Scores are supervised class-1 model outputs, not calibrated cheating probabilities or proof of cheating.",
            "Player scores are equal-weight window means; overlapping shot windows are not independent evidence.",
            "Review candidates are the three highest-scoring windows per player, even at low scores; no validated threshold is applied.",
            "Behavioral speed and acceleration indicators have physical units; they are not anomaly scores or probabilities and are not combined.",
            "Global feature importance describes the model as a whole; measured window features do not identify local causal contributions.",
            "Local RF/tree contributions telescope class-1 probabilities along existing tree paths. They depend on split order and are not causal effects or SHAP values; other model families have no local attribution here.",
            "M5 was evaluated on CS2CD. Accuracy and calibration on ordinary demos have not been validated.",
            "Historical M5 metadata omits extraction settings; 32 ticks and 64 Hz follow the M3/M5 training scripts. Compatibility checks cannot establish scientific validity.",
            "Tracking uses observed victim positions only, without visibility, eye-height or hitbox reconstruction. Shot-direction plots are not target tracking.",
            "Nearby hits and kills belong to the same attacker, weapon and round in the next two ticks; this temporal association does not prove which shot caused an event.",
            "Players without complete finite windows remain in the report with no score. No minimum observation count was validated in M5.",
        ],
    }
    if any(w["round_number"] is None for w in scored_windows):
        report["limitations"].append(
            f"{missing_round_count} scored shots have no completed round association; round_number is null. "
            "Completed intervals end at round_end; shots in inter-round gaps or outside available coverage remain in player scores."
        )
    if any(w["crosses_round_boundary"] for w in scored_windows):
        report["limitations"].append(
            f"{boundary_count} windows cross round boundaries; the round number refers to the shot tick. "
            "Historical M3 windows remain unchanged: 32 player samples ending at the shot, without round filtering. "
            "A boundary flag alone does not establish invalid aim data."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    for window in review_events:
        window["visualization"] = (_plot_review_window(window, ticks, window["events"], output_dir)
                                   if review_plots else {"path": None, "reason": "Review plots disabled for batch evaluation"})
    write_report(report, output_dir)
    return report


def write_report(report: dict, output_dir: Path) -> None:
    """Persist the complete machine-readable report and a readable inspection guide."""
    (output_dir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    lines = ["# CS2Guard match analysis", "", f"Demo: {report['match']['demo_path']}",
             f"Map: {report['match'].get('map_name')}",
             f"Model: {report['model']['model_name']} {report['model']['version']}",
             f"Status: {report['summary']['status']}",
             f"Players: {report['summary']['player_count']}; scored: {report['summary']['scored_player_count']}; windows: {report['summary']['window_count']}",
             f"Unscored shots: {report['summary']['unscored_shot_count']}; windows without completed round: {report['summary']['missing_round_window_count']}; windows crossing round boundaries: {report['summary']['cross_round_window_count']}",
             "", "Scores are uncalibrated supervised model outputs. They are not proof of cheating.", "",
             "| Rank | Player | ID | Mean score | Windows | Unscored shots | Status |",
             "|---|---|---|---|---|---|---|"]
    for player in report["players"]:
        name = player["player_name"].replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        score = f"{player['score']:.6f}" if player["score"] is not None else "N/A"
        lines.append(f"| {player['rank'] or ''} | {name} | {player['player_id']} | {score} | {player['window_count']} | {player['unscored_shot_count']} | {player['status']} |")
    lines.extend(["", "## Behavioral indicators", "", "Speed and acceleration are equal-weight means across scored shot windows. Tracking is available only in observed-victim plots; reaction is unavailable.", "",
                  "| Player ID | Mean angular speed (degrees/s) | Mean angular acceleration (degrees/s²) |", "|---|---|---|"])
    for player in report["players"]:
        behavior = player["behavioral_scores"]
        lines.append(f"| {player['player_id']} | {behavior['angular_speed']['value']} | {behavior['angular_acceleration']['value']} |")
    lines.extend(["", "## Player model contributions", "", "For RF/trees, root baseline plus signed feature contributions reconstructs the mean score. These are path-dependent, not causal effects or SHAP values."])
    for player in report["players"]:
        contribution = player["model_contributions"]
        if contribution is not None:
            lines.extend(["", f"Player: {player['player_id']}; root baseline: {contribution['baseline']:.6f}", "",
                          "| Feature | Mean signed probability change |", "|---|---|"])
            lines.extend(f"| {name} | {value:.6f} |" for name, value in contribution["features"].items())
    lines.extend(["", "## Rounds ordered for inspection", "", "Priority is the maximum window score in the round, not a calibrated round probability.", "",
                  "| Round | Ticks | Windows | Maximum window score |", "|---|---|---|---|"])
    for r in report["rounds"]:
        lines.append(f"| {r['number']} | {r['start_tick']}–{r['end_tick']} | {r['window_count']} | {r['max_window_score']} |")
    lines.extend(["", "## Review sequences", "", "Candidates are inspection priorities, not cheat classifications."])
    for window in report["review_events"]:
        lines.extend(["", f"### {window['player_id']} — round {window['round_number']}, shot tick {window['shot_tick']}", "",
                      f"Window: {window['window_id']}; ticks {window['start_tick']}–{window['end_tick']}; score {window['score']:.6f}",
                      "", window["explanation"], "", "| Measured feature | Value |", "|---|---|"])
        lines.extend(f"| {name} | {value} |" for name, value in window["features"].items())
        contribution = window["model_contributions"]
        if contribution is not None:
            lines.extend(["", f"Root probability baseline: {contribution['baseline']:.6f}", "",
                          "| Feature | Signed path probability change |", "|---|---|"])
            lines.extend(f"| {name} | {value:.6f} |" for name, value in contribution["features"].items())
        else:
            lines.extend(["", "Local model contributions unavailable for this estimator family."])
        lines.extend(["", "Events: " + ", ".join(f"{e['event_id']} {e['event_type']} at {e['tick']}" for e in window["events"]), ""])
        visual = window["visualization"]
        if visual["path"]:
            lines.extend([f"Reference: {visual['reference']}; target: {visual.get('target_id')}", "",
                          f"![Aim sequence]({visual['path']})", ""])
            if visual.get("tracking"):
                lines.append(f"Descriptive tracking: {json.dumps(visual['tracking'], ensure_ascii=False)}")
            elif visual.get("tracking_unavailable_reason"):
                lines.append(f"Tracking unavailable: {visual['tracking_unavailable_reason']}")
        else:
            lines.append(f"Visualization unavailable: {visual['reason']}")
    lines.extend(["", "## Global model importance", "", "Global importance is not local attribution.", "", json.dumps(report["feature_importance"]["values"], ensure_ascii=False),
                  "", "## Interpretation limits", ""])
    lines.extend(f"- {limit}" for limit in report["limitations"])
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
