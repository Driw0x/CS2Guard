import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from cs2guard_demo.detection import FEATURE_COLUMNS, run_lof

INPUT = ROOT / "data" / "processed" / "aim_features.csv"
BASELINE_INPUT = ROOT / "data" / "processed" / "lof_players.csv"
OUTPUT = ROOT / "data" / "processed" / "lof_feature_ablation.csv"


def player_auc(players: pd.DataFrame) -> float:
    labeled = players.dropna(subset=["label"])
    y_true = (labeled["label"] == "suspicious").astype(int)
    return roc_auc_score(y_true, labeled["mean_anomaly_score"])


def main() -> None:
    df = pd.read_csv(INPUT)
    baseline_players = pd.read_csv(BASELINE_INPUT)
    baseline_auc = player_auc(baseline_players)

    results = []

    for removed_feature in FEATURE_COLUMNS:
        features = [
            feature for feature in FEATURE_COLUMNS
            if feature != removed_feature
        ]

        windows, players = run_lof(df, feature_columns=features)
        auc = player_auc(players)

        results.append(
            {
                "removed_feature": removed_feature,
                "roc_auc": auc,
                "auc_drop": baseline_auc - auc,
            }
        )

        print(
            f"{removed_feature}: "
            f"ROC-AUC={auc:.6f} "
            f"drop={baseline_auc - auc:+.6f}"
        )

        del windows
        del players

    results_df = pd.DataFrame(results).sort_values(
        "auc_drop",
        ascending=False,
    )
    results_df.to_csv(OUTPUT, index=False)

    print(f"\nBaseline ROC-AUC: {baseline_auc:.6f}")
    print("\n=== FEATURE ABLATION ===")
    print(results_df.to_string(index=False))
    print(f"\nResults saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
