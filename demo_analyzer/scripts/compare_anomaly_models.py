from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "processed"

MODEL_FILES = {
    "isolation_forest": DATA_DIR / "anomaly_players.csv",
    "lof": DATA_DIR / "lof_players.csv",
    "one_class_svm": DATA_DIR / "ocsvm_players.csv",
}

SCORE_COLUMNS = [
    "mean_anomaly_score",
    "max_anomaly_score",
    "anomalous_window_ratio",
]

OUTPUT = DATA_DIR / "anomaly_model_comparison.csv"


def main() -> None:
    results = []
    reference_players = None

    for model_name, path in MODEL_FILES.items():
        df = pd.read_csv(path)
        df = df.dropna(subset=["label"]).copy()

        players = set(zip(df["source"], df["match_id"], df["player_id"]))
        if reference_players is None:
            reference_players = players
        elif players != reference_players:
            raise ValueError("Models do not contain the same labeled players")

        y_true = (df["label"] == "suspicious").astype(int)

        for score_column in SCORE_COLUMNS:
            auc = roc_auc_score(y_true, df[score_column])
            results.append(
                {
                    "model": model_name,
                    "score": score_column,
                    "roc_auc": auc,
                }
            )

    comparison = pd.DataFrame(results).sort_values("roc_auc", ascending=False)
    comparison.to_csv(OUTPUT, index=False)

    print("=== ANOMALY MODEL COMPARISON ===")
    print(comparison.to_string(index=False))

    best = comparison.iloc[0]
    print(
        f"\nBest: {best['model']} / {best['score']} "
        f"(ROC-AUC={best['roc_auc']:.4f})"
    )
    print(f"\nComparison saved to: {OUTPUT}")


if __name__ == "__main__":
    main()