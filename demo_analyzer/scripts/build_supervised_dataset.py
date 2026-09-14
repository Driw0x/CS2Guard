from pathlib import Path

import pandas as pd

from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS
from cs2guard_demo.supervised.dataset import build_labeled_dataset

INPUT = Path("data/processed/aim_features.csv")
OUTPUT = Path("data/processed/supervised_dataset.csv")


def main() -> None:
    df = pd.read_csv(INPUT)
    dataset = build_labeled_dataset(df)
    dataset.to_csv(OUTPUT, index=False)

    print("=== SUPERVISED DATASET ===")
    print(f"Samples: {len(dataset)}")
    print(f"Matches: {dataset['match_id'].nunique()}")
    print(f"Players: {dataset['player_id'].nunique()}")
    print(f"Features: {len(FEATURE_COLUMNS)}")
    print()
    print("=== LABEL DISTRIBUTION ===")
    print(dataset["label"].value_counts().to_string())
    print()
    print(f"Dataset saved to: {OUTPUT}")


if __name__ == "__main__":
    main()