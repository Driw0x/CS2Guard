from pathlib import Path

import pandas as pd
from demoparser2 import DemoParser as Demoparser2


class DemoParser:
    def __init__(self, demo_path: str | Path):
        self.demo_path = Path(demo_path)

        if not self.demo_path.exists():
            raise FileNotFoundError(
                f"Demo file not found: {self.demo_path}"
            )

        self.parser = Demoparser2(str(self.demo_path))

        self.match_start_tick = self._get_match_start_tick()

    def _get_match_start_tick(self) -> int:
        new_match = self.parser.parse_event("begin_new_match")

        if new_match.empty:
            raise ValueError(
                "Unable to find the beginning of the match."
            )

        return int(new_match.iloc[-1]["tick"])

    def get_shots(self):
        shots = self.parser.parse_event("weapon_fire")

        shots = shots[shots["tick"] >= self.match_start_tick]

        return (
            shots[
                [
                    "tick",
                    "user_steamid",
                    "user_name",
                    "weapon",
                ]
            ]
            .dropna(subset=["user_steamid"])
            .reset_index(drop=True)
        )

    def get_hits(self):
        hits = self.parser.parse_event("player_hurt")

        hits = hits[hits["tick"] >= self.match_start_tick]

        return (
            hits[
                [
                    "tick",
                    "attacker_steamid",
                    "attacker_name",
                    "user_steamid",
                    "user_name",
                    "weapon",
                    "dmg_health",
                    "dmg_armor",
                    "health",
                    "armor",
                    "hitgroup",
                ]
            ]
            .dropna(subset=["attacker_steamid", "user_steamid"])
            .reset_index(drop=True)
        )

    def get_kills(self):
        kills = self.parser.parse_event("player_death")

        kills = kills[kills["tick"] >= self.match_start_tick]

        return (
            kills[
                [
                    "tick",
                    "attacker_steamid",
                    "attacker_name",
                    "user_steamid",
                    "user_name",
                    "weapon",
                    "headshot",
                    "distance",
                    "hitgroup",
                    "noscope",
                    "penetrated",
                    "thrusmoke",
                    "attackerblind",
                    "attackerinair",
                ]
            ]
            .dropna(subset=["user_steamid"])
            .reset_index(drop=True)
        )

    def get_player_ticks(self):
        ticks = self.parser.parse_ticks([
            "X",
            "Y",
            "Z",
            "yaw",
            "pitch",
            "team_name",
        ])

        ticks = ticks[ticks["tick"] >= self.match_start_tick]

        return (
            ticks[
                [
                    "tick",
                    "steamid",
                    "name",
                    "team_name",
                    "X",
                    "Y",
                    "Z",
                    "yaw",
                    "pitch",
                ]
            ]
            .dropna(
                subset=[
                    "steamid",
                    "team_name",
                    "X",
                    "Y",
                    "Z",
                    "yaw",
                    "pitch",
                ]
            )
            .reset_index(drop=True)
        )
    
    def get_match_metadata(self) -> dict:
        header = self.parser.parse_header()

        return {
            "map_name": header.get("map_name"),
            "patch_version": header.get("patch_version"),
            "demo_version": header.get("demo_version_name"),
        }
    
    def get_players(self):
        ticks = self.parser.parse_ticks([
            "team_name",
        ])

        return (
            ticks[["steamid", "name"]]
            .dropna(subset=["steamid"])
            .drop_duplicates(subset=["steamid"])
            .reset_index(drop=True)
        )
    
    def get_player_teams(self):
        ticks = self.parser.parse_ticks([
            "team_name",
        ])

        return (
            ticks[["tick", "steamid", "name", "team_name"]]
            .dropna(subset=["steamid"])
            .reset_index(drop=True)
        )

    def get_rounds(self):
        starts = self.parser.parse_event("round_start")
        ends = self.parser.parse_event("round_end")

        starts = (
            starts[starts["tick"] > self.match_start_tick]
            .sort_values("tick")
            .reset_index(drop=True)
        )

        ends = (
            ends[ends["tick"] > self.match_start_tick]
            .sort_values("tick")
            .reset_index(drop=True)
        )

        rounds = []

        for index, end in ends.iterrows():
            if index == 0:
                start_tick = self.match_start_tick
            else:
                previous_starts = starts[starts["tick"] < end["tick"]]

                if previous_starts.empty:
                    continue

                start_tick = int(previous_starts.iloc[-1]["tick"])

            rounds.append({
                "round": index + 1,
                "start_tick": start_tick,
                "end_tick": int(end["tick"]),
                "winner": end["winner"],
                "reason": end["reason"],
            })

        return rounds