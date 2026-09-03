from pathlib import Path

from cs2guard_demo.dataset.builder import DatasetBuilder

import json

from cs2guard_demo.dataset.statistics import generate_dataset_statistics


DEMO_DIRECTORY = Path("data/raw")
OUTPUT_DIRECTORY = Path("data/processed")


def main() -> None:
    builder = DatasetBuilder()

    builder.process_directory(DEMO_DIRECTORY)

    dataset = builder.build()
    player_dataset = builder.build_player_samples()
    temporal_windows = (
        builder.build_temporal_windows(
            DEMO_DIRECTORY,
            window_size=32,
        )
    )
    aim_features = builder.build_aim_features(
        temporal_windows,
        tick_rate=64.0,
    )
    statistics = generate_dataset_statistics(
        event_dataset=dataset,
        player_dataset=player_dataset,
        temporal_windows=temporal_windows,
        aim_features=aim_features,
    )

    print()
    print("=== DATASET PREVIEW ===")
    print(dataset.head())

    print()
    print("=== DATASET SUMMARY ===")
    print(f"Samples: {len(dataset)}")
    print(f"Matches: {dataset['match_id'].nunique()}")
    print(f"Players: {dataset['steamid'].nunique()}")
    print()
    print("Events:")
    print(dataset["event_type"].value_counts())

    print()
    print("=== PLAYER DATASET PREVIEW ===")
    print(player_dataset.head())

    print()
    print("=== PLAYER DATASET SUMMARY ===")
    print(f"Player samples: {len(player_dataset)}")

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = OUTPUT_DIRECTORY / "dataset.csv"

    dataset.to_csv(
        output_path,
        index=False,
    )

    print()
    print(f"Dataset saved to: {output_path}")

    player_output_path = (
        OUTPUT_DIRECTORY / "player_dataset.csv"
    )

    player_dataset.to_csv(
        player_output_path,
        index=False,
    )

    print(
        f"Player dataset saved to: "
        f"{player_output_path}"
    )

    temporal_output_path = (
        OUTPUT_DIRECTORY
        / "temporal_windows.csv"
    )

    temporal_windows.to_csv(
        temporal_output_path,
        index=False,
    )

    print()
    print("=== TEMPORAL WINDOWS SUMMARY ===")

    if temporal_windows.empty:
        print("No temporal windows generated.")
    else:
        print(
            f"Windows: "
            f"{temporal_windows['window_id'].nunique()}"
        )
        print(
            f"Rows: {len(temporal_windows)}"
        )

    print(
        f"Temporal windows saved to: "
        f"{temporal_output_path}"
    )

    aim_features_output_path = (
        OUTPUT_DIRECTORY
        / "aim_features.csv"
    )

    aim_features.to_csv(
        aim_features_output_path,
        index=False,
    )

    print()
    print("=== AIM FEATURES SUMMARY ===")

    if aim_features.empty:
        print("No aim features generated.")
    else:
        print(
            f"Feature samples: "
            f"{len(aim_features)}"
        )
        print(
            f"Matches: "
            f"{aim_features['match_id'].nunique()}"
        )
        print(
            f"Players: "
            f"{aim_features['steamid'].nunique()}"
        )

    print(
        f"Aim features saved to: "
        f"{aim_features_output_path}"
    )

    statistics_output_path = OUTPUT_DIRECTORY / "dataset_statistics.json"

    with statistics_output_path.open("w", encoding="utf-8") as file:
        json.dump(statistics, file, indent=4, ensure_ascii=False)

    print(f"Dataset statistics saved to: {statistics_output_path}")


if __name__ == "__main__":
    main()