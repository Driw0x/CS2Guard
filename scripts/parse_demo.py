from pathlib import Path

from src.cs2guard.parser.demo_parser import DemoParser


ROOT_DIR = Path(__file__).resolve().parent.parent
DEMO_PATH = ROOT_DIR / "data" / "raw" / "demos" / "test.dem"


def main():
    parser = DemoParser(DEMO_PATH)
    match = parser.get_match()

    print(f"Map: {match.map_name}")
    print(f"Patch: {match.patch_version}")
    print(f"Players: {len(match.players)}")
    print(f"Rounds: {len(match.rounds)}")
    print(f"Events: {len(match.events)}")


if __name__ == "__main__":
    main()