import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from cs2guard_demo.detection.anomaly import compute_suspicion_scores

INPUT = ROOT / "data" / "processed" / "lof_players.csv"
OUTPUT = ROOT / "data" / "processed" / "suspicion_scores.csv"


def main() -> None:
    players = pd.read_csv(INPUT)
    scored = compute_suspicion_scores(players)
    scored.to_csv(OUTPUT, index=False)

    print("=== SUSPICION SCORES ===")
    print(f"Players: {len(scored)}")

    labeled = scored.dropna(subset=["label"])

    print("\n=== SCORES BY LABEL ===")
    print(
        labeled.groupby("label")["suspicion_score"]
        .agg(["count", "mean", "median"])
    )

    print("\n=== HIGHEST SCORES ===")
    print(
        scored.sort_values("suspicion_score", ascending=False)[
            [
                "match_id",
                "player_id",
                "label",
                "mean_anomaly_score",
                "suspicion_score",
            ]
        ].head(20).to_string(index=False)
    )

    print(f"\nSuspicion scores saved to: {OUTPUT}")


if __name__ == "__main__":
    main()