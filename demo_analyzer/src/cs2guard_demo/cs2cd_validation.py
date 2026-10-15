"""Player-match metrics for frozen M6 evaluation on canonical CS2CD features."""

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from cs2guard_demo.supervised import LABEL_TO_TARGET, evaluate_predictions, evaluate_ranked_scores
from cs2guard_demo.validation import THRESHOLDS


def rank_players(players: pd.DataFrame) -> pd.DataFrame:
    """Use M6's descending score and ascending canonical player-ID tie break."""
    required = {"match_id", "player_id", "label", "score"}
    if required - set(players):
        raise ValueError(f"Missing player columns: {sorted(required - set(players))}")
    if players.empty or players[["match_id", "player_id", "label"]].isna().any().any():
        raise ValueError("Player identities and labels must be present")
    if players.duplicated(["match_id", "player_id"]).any():
        raise ValueError("Duplicate player-match observations")
    if not players.label.isin(LABEL_TO_TARGET).all():
        raise ValueError("Unknown player labels")
    ranked = players.copy()
    ranked["score"] = pd.to_numeric(ranked.score, errors="coerce")
    if not np.isfinite(ranked.score).all() or not ranked.score.between(0, 1).all():
        raise ValueError("Player scores must be finite and between zero and one")
    ranked = ranked.sort_values(["match_id", "score", "player_id"], ascending=[True, False, True]).reset_index(drop=True)
    ranked["rank"] = ranked.groupby("match_id", sort=False).cumcount() + 1
    return ranked


def classification_summary(players: pd.DataFrame) -> dict:
    """Evaluate equally weighted player-matches and hits in positive matches."""
    ranked = rank_players(players)
    targets = ranked.label.map(LABEL_TO_TARGET)
    both_classes = targets.nunique() == 2
    discrimination = evaluate_ranked_scores(ranked, "score") if both_classes else {"roc_auc": None, "pr_auc": None}
    positive_matches = set(ranked.loc[targets.eq(1), "match_id"])
    thresholds = []
    for threshold in THRESHOLDS:
        predicted = ranked.score.ge(threshold)
        if both_classes:
            metrics = evaluate_predictions(targets, predicted.astype(int), ranked.score)
        else:
            tn, fp = int((targets.eq(0) & ~predicted).sum()), int((targets.eq(0) & predicted).sum())
            fn, tp = int((targets.eq(1) & ~predicted).sum()), int((targets.eq(1) & predicted).sum())
            metrics = {"tn": tn, "fp": fp, "fn": fn, "tp": tp,
                       "precision": tp / (tp + fp) if tp + fp else 0.0,
                       "recall": tp / (tp + fn) if tp + fn else None,
                       "f1": 2 * tp / (2 * tp + fp + fn) if tp + fn else None,
                       "false_positive_rate": fp / (fp + tn) if fp + tn else None}
        thresholds.append({"threshold": threshold, "comparison": ">=",
                           **{key: value for key, value in metrics.items() if key not in {"roc_auc", "pr_auc"}}})
    hits = {}
    for k in (1, 3):
        found = ranked.loc[ranked["rank"].le(k) & ranked.label.eq("suspicious"), "match_id"].nunique()
        hits[f"hit_at_{k}"] = found / len(positive_matches) if positive_matches else None
    return {"counts": {"matches": int(ranked.match_id.nunique()), "player_matches": len(ranked),
                       "legitimate_player_matches": int(targets.eq(0).sum()),
                       "suspicious_player_matches": int(targets.eq(1).sum()),
                       "positive_matches": len(positive_matches), "positive_prevalence": float(targets.mean())},
            "discrimination": discrimination, "thresholds": thresholds, **hits}


def cluster_bootstrap(players: pd.DataFrame, *, seed: int = 42, draws: int = 5000) -> dict:
    """Resample complete matches; multiplicity weights equal concatenated draws.

    Intervals condition on the frozen model and independence between matches.
    Match-scoped anonymous IDs cannot identify real players recurring in matches.
    AUC intervals exclude draws without both classes. Recall/F1/hit intervals
    require positive observations; FPR intervals require negative observations.
    Precision
    without predicted positives is zero, matching the existing sklearn convention.
    """
    if not isinstance(draws, int) or draws < 100 or not isinstance(seed, int) or seed < 0:
        raise ValueError("At least 100 bootstrap draws and a nonnegative integer seed required")
    ranked = rank_players(players)
    targets = ranked.label.map(LABEL_TO_TARGET).to_numpy(dtype=int)
    scores = ranked.score.to_numpy(dtype=float)
    matches = sorted(ranked.match_id.unique())
    groups = len(matches)
    codes = pd.Categorical(ranked.match_id, categories=matches).codes
    samples = np.random.default_rng(seed).integers(0, groups, size=(draws, groups))
    multiplicities = np.zeros((draws, groups), dtype=int)
    np.add.at(multiplicities, (np.arange(draws)[:, None], samples), 1)
    positive_counts = np.bincount(codes, weights=targets, minlength=groups)
    negative_counts = np.bincount(codes, weights=1 - targets, minlength=groups)
    has_positive = multiplicities @ positive_counts > 0
    has_negative = multiplicities @ negative_counts > 0
    both_classes = has_positive & has_negative
    weights = multiplicities
    result = {"method": "percentile_match_bootstrap", "confidence": .95, "groups": groups,
              "draws": draws, "seed": seed, "discrimination_valid_draws": int(both_classes.sum()),
              "positive_draws": int(has_positive.sum()), "negative_draws": int(has_negative.sum()),
              "precision_zero_division": 0, "conditional_on_independent_matches": True}

    def interval(values):
        values = np.asarray(values, dtype=float)
        if groups < 2 or not len(values):
            return {"interval": None, "degenerate": False, "valid_draws": len(values)}
        return {"interval": np.quantile(values, [.025, .975]).tolist(),
                "degenerate": bool(np.ptp(values) == 0), "valid_draws": len(values)}

    auc, ap = [], []
    if groups >= 2:
        for counts in weights[both_classes]:
            observation_weights = counts[codes]
            auc.append(roc_auc_score(targets, scores, sample_weight=observation_weights))
            ap.append(average_precision_score(targets, scores, sample_weight=observation_weights))
    result["discrimination"] = {"roc_auc": interval(auc), "pr_auc": interval(ap)}

    predicted = scores[:, None] >= np.asarray(THRESHOLDS)
    actual = targets[:, None].astype(bool)
    # Summed confusion counts preserve every player when a match is drawn twice.
    confusion = np.zeros((groups, len(THRESHOLDS), 4), dtype=int)
    np.add.at(confusion, codes, np.stack([~actual & ~predicted, ~actual & predicted,
                                        actual & ~predicted, actual & predicted], axis=-1))
    totals = (weights @ confusion.reshape(groups, -1)).reshape(-1, len(THRESHOLDS), 4)
    tn, fp, fn, tp = [totals[:, :, index] for index in range(4)]

    def ratio(numerator, denominator):
        return np.divide(numerator, denominator, out=np.zeros_like(numerator, dtype=float), where=denominator != 0)

    metrics = {"precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
               "f1": ratio(2 * tp, 2 * tp + fp + fn), "false_positive_rate": ratio(fp, fp + tn)}
    masks = {"precision": np.ones(draws, dtype=bool), "recall": has_positive,
             "f1": has_positive, "false_positive_rate": has_negative}
    result["thresholds"] = [{"threshold": threshold,
                             **{name: interval(values[masks[name], index]) for name, values in metrics.items()}}
                            for index, threshold in enumerate(THRESHOLDS)]
    positive = (positive_counts > 0).astype(int)
    for k in (1, 3):
        hit_matches = set(ranked.loc[ranked["rank"].le(k) & ranked.label.eq("suspicious"), "match_id"])
        hits = np.array([match in hit_matches for match in matches], dtype=int)
        result[f"hit_at_{k}"] = interval(ratio(weights[has_positive] @ hits, weights[has_positive] @ positive))
    return result
