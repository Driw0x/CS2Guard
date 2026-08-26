from pathlib import Path

from src.cs2guard.parser.demo_parser import DemoParser

# M1

ROOT_DIR = Path(__file__).resolve().parent.parent
demo_name = "test.dem"
demo_path = ROOT_DIR / "data" / "raw" / "demos" / demo_name

parser = DemoParser(demo_path)
metadata = parser.get_match_metadata()

# print(metadata)

deaths = parser.get_deaths()

# print(deaths)

ticks = parser.get_player_ticks()

# print(ticks.columns)
# print(ticks.head())
# print(ticks.shape)
# print(ticks.isna().sum())

players = parser.get_players()
teams = parser.get_player_teams()

# print(players)
# print(f"Players found: {len(players)}")

# print(teams.head(20))

rounds = parser.get_rounds()

# for round_data in rounds:
#     print(round_data)

shots = parser.get_shots()
hits = parser.get_hits()
kills = parser.get_kills()

print("Shots:", len(shots))
print(shots.head())

print("Hits:", len(hits))
print(hits.head())

print("Kills:", len(kills))
print(kills.head())