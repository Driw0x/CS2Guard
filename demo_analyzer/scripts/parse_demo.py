from pathlib import Path

from cs2guard_demo.parser.demo_parser import DemoParser


ROOT_DIR = Path(__file__).resolve().parents[2]

DEMO_PATH = (
    ROOT_DIR
    / "data"
    / "raw"
    / "demos"
    / "test.dem"
)


def main():
    parser = DemoParser(
        DEMO_PATH
    )

    match = parser.get_match()

    print("=== DEMO PARSER ===")

    print(
        f"Map: {match.map_name}"
    )

    print(
        f"Patch: {match.patch_version}"
    )

    print(
        f"Players: {len(match.players)}"
    )

    print(
        f"Rounds: {len(match.rounds)}"
    )

    print(
        f"Events: {len(match.events)}"
    )

    ticks = parser.get_player_ticks()
    shots = parser.get_shots()
    hits = parser.get_hits()
    kills = parser.get_kills()

    print("\n=== EXTRACTED DATA ===")

    print(
        f"Player ticks: {len(ticks)}"
    )

    print(
        f"Shots: {len(shots)}"
    )

    print(
        f"Hits: {len(hits)}"
    )

    print(
        f"Kills: {len(kills)}"
    )


if __name__ == "__main__":
    main()