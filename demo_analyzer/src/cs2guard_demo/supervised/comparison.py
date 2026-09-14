import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

from cs2guard_demo.supervised.dataset import LABEL_TO_TARGET


def aggregate_player_scores(
    df: pd.DataFrame,
    scores,
    score_name: str,
) -> pd.DataFrame:
    if len(df) != len(scores):
        raise ValueError("Scores must match dataset length")

    data = df[["match_id", "player_id", "label"]].copy()
    data[score_name] = scores

    if data.groupby(["match_id", "player_id"])["label"].nunique().max() > 1:
        raise ValueError("Inconsistent player labels")

    return data.groupby(["match_id", "player_id"], as_index=False).agg(
        label=("label", "first"),
        **{score_name: (score_name, "mean")},
    )


def evaluate_ranked_scores(
    player_scores: pd.DataFrame,
    score_name: str,
) -> dict[str, float]:
    targets = player_scores["label"].map(LABEL_TO_TARGET)
    scores = pd.to_numeric(player_scores[score_name], errors="coerce")

    if targets.isna().any():
        raise ValueError("Unknown labels")
    if targets.nunique() != 2:
        raise ValueError("Both labels are required")
    if not np.isfinite(scores).all():
        raise ValueError("Scores contain NaN or infinite values")

    return {
        "roc_auc": roc_auc_score(targets, scores),
        "pr_auc": average_precision_score(targets, scores),
    }


def score_lof_held_out(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    n_neighbors: int = 20,
) -> np.ndarray:
    if not 1 <= n_neighbors < len(X_train):
        raise ValueError("n_neighbors must be smaller than the training set")

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LocalOutlierFactor(
        n_neighbors=n_neighbors,
        contamination="auto",
        novelty=True,
        n_jobs=-1,
    )
    model.fit(X_train_scaled)

    return -model.score_samples(X_test_scaled)