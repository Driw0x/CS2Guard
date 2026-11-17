"""Build the M7 fixed-length temporal dataset from canonical M3 outputs."""

import argparse
from pathlib import Path

import pandas as pd

from cs2guard_demo.temporal import build_sequence_arrays_from_csv, create_match_splits, save_temporal_dataset


ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", type=Path, default=ROOT / "data" / "processed" / "temporal_windows.csv")
    parser.add_argument("--features", type=Path, default=ROOT / "data" / "processed" / "aim_features.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "processed" / "temporal_dataset.npz")
    parser.add_argument("--limit", type=int, help="Development-only maximum feature rows")
    parser.add_argument("--chunk-size", type=int, default=500_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features = pd.read_csv(args.features)
    if args.limit:
        features = features.head(args.limit)
    splits = create_match_splits(features)
    arrays = build_sequence_arrays_from_csv(args.windows, features, splits=splits, chunk_size=args.chunk_size)
    dataset_path, metadata_path = save_temporal_dataset(arrays, args.output)
    print(f"Sequences: {len(arrays['X'])}")
    for name in ("train", "validation", "test"):
        print(f"{name}: {(arrays['split'] == name).sum()}")
    print(f"Dataset: {dataset_path}")
    print(f"Metadata: {metadata_path}")


if __name__ == "__main__":
    main()
