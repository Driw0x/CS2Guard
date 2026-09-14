from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PLAYER_INPUT = ROOT / "data" / "processed" / "lof_players.csv"
WINDOW_INPUT = ROOT / "data" / "processed" / "lof_windows.csv"
BASELINE_INPUT = ROOT / "data" / "processed" / "legitimate_baseline.csv"

FEATURE_COLUMNS = [
    "mean_angular_speed",
    "max_angular_speed",
    "std_angular_speed",
    "mean_angular_acceleration",
    "max_angular_acceleration",
    "std_angular_acceleration",
]

TOP_PLAYERS = 10
TOP_WINDOWS = 3


def main() -> None:
    players = pd.read_csv(PLAYER_INPUT)
    windows = pd.read_csv(WINDOW_INPUT)
    baseline = pd.read_csv(BASELINE_INPUT, index_col=0)

    top_players = (
        players[players["label"] == "legitimate"]
        .sort_values("mean_anomaly_score", ascending=False)
        .head(TOP_PLAYERS)
    )

    p99 = baseline["99%"]

    print("=== HIGH-SCORING LEGITIMATE PLAYERS ===")

    for _, player in top_players.iterrows():
        player_windows = windows[
            (windows["match_id"] == player["match_id"])
            & (windows["player_id"] == player["player_id"])
        ].sort_values("anomaly_score", ascending=False)

        print(
            f"\n{player['player_id']} "
            f"windows={player['window_count']} "
            f"mean={player['mean_anomaly_score']:.4f} "
            f"ratio={player['anomalous_window_ratio']:.4f}"
        )

        for _, window in player_windows.head(TOP_WINDOWS).iterrows():
            exceeded = [
                feature
                for feature in FEATURE_COLUMNS
                if window[feature] > p99[feature]
            ]

            print(
                f"  window={window['window_id']} "
                f"score={window['anomaly_score']:.4f} "
                f"p99_exceeded={exceeded}"
            )


if __name__ == "__main__":
    main()