import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from cs2guard_demo.detection.anomaly import (
    run_isolation_forest,
    run_lof,
    run_one_class_svm,
)

DEFAULT_INPUT = ROOT / "data" / "processed" / "aim_features.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        choices=["isolation_forest", "lof", "one_class_svm"],
        default="isolation_forest",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = pd.read_csv(args.input)

    if args.model == "isolation_forest":
        scored_windows, scored_players = run_isolation_forest(df)
        window_output = ROOT / "data" / "processed" / "anomaly_windows.csv"
        player_output = ROOT / "data" / "processed" / "anomaly_players.csv"
    elif args.model == "lof":
        scored_windows, scored_players = run_lof(df)
        window_output = ROOT / "data" / "processed" / "lof_windows.csv"
        player_output = ROOT / "data" / "processed" / "lof_players.csv"
    else:
        scored_windows, scored_players = run_one_class_svm(df)
        window_output = ROOT / "data" / "processed" / "ocsvm_windows.csv"
        player_output = ROOT / "data" / "processed" / "ocsvm_players.csv"

    scored_windows.to_csv(window_output, index=False)
    scored_players.to_csv(player_output, index=False)

    print(f"=== {args.model.upper()} ANOMALY DETECTION ===")
    print(f"Windows: {len(scored_windows)}")
    print(f"Players: {len(scored_players)}")
    print(f"Anomalous windows: {scored_windows['is_anomaly'].sum()}")

    labeled = scored_players.dropna(subset=["label"])

    print("\n=== PLAYER SCORES BY LABEL ===")
    print(
        labeled.groupby("label")["mean_anomaly_score"]
        .agg(["count", "mean", "median"])
    )

    print(f"\nWindow scores saved to: {window_output}")
    print(f"Player scores saved to: {player_output}")


if __name__ == "__main__":
    main()