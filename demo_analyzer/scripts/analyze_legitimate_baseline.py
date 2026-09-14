from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from cs2guard_demo.detection.anomaly import FEATURE_COLUMNS

INPUT = ROOT / "data" / "processed" / "aim_features.csv"
OUTPUT = ROOT / "data" / "processed" / "legitimate_baseline.csv"


def main() -> None:
    df = pd.read_csv(INPUT)
    legitimate = df[df["label"] == "legitimate"]

    baseline = legitimate[FEATURE_COLUMNS].describe(
        percentiles=[0.25, 0.5, 0.75, 0.95, 0.99]
    ).T

    baseline.to_csv(OUTPUT)

    print("=== LEGITIMATE BEHAVIOR BASELINE ===")
    print(f"Windows: {len(legitimate)}")
    print(baseline)
    print(f"\nBaseline saved to: {OUTPUT}")


if __name__ == "__main__":
    main()