from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "processed" / "lof_windows.csv"
OUTPUT = ROOT / "data" / "processed" / "shot_anomaly_scores.csv"

EVENT_COLUMNS = [
    "window_id",
    "source",
    "match_id",
    "player_id",
    "source_player_id",
    "identity_scope",
    "shot_tick",
    "weapon",
    "label",
    "anomaly_score",
    "is_anomaly",
]


def main() -> None:
    df = pd.read_csv(INPUT)

    missing = [column for column in EVENT_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing event score columns: {missing}")

    events = df[EVENT_COLUMNS].copy()
    events.to_csv(OUTPUT, index=False)

    print("=== SHOT-LEVEL ANOMALY SCORES ===")
    print(f"Events: {len(events)}")
    print(f"Unique windows: {events['window_id'].nunique()}")
    print(f"Anomalous events: {events['is_anomaly'].sum()}")

    labeled = events.dropna(subset=["label"])

    print("\n=== EVENT SCORES BY LABEL ===")
    print(
        labeled.groupby("label")["anomaly_score"]
        .agg(["count", "mean", "median"])
    )

    print(f"\nEvent scores saved to: {OUTPUT}")


if __name__ == "__main__":
    main()