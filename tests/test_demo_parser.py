import pandas as pd

from src.cs2guard.parser.demo_parser import DemoParser


class FakeParser:
    """
    Fake demoparser2 parser used to test CS2Guard
    without requiring a real .dem file.
    """

    def parse_ticks(self, fields):
        return pd.DataFrame({
            "tick": [50, 100, 101, 102],
            "steamid": [1, 1, 2, 2],
            "name": ["PlayerA", "PlayerA", "PlayerB", "PlayerB"],
            "team_name": ["CT", "CT", "TERRORIST", None],
            "X": [10.0, 20.0, 30.0, None],
            "Y": [15.0, 25.0, 35.0, None],
            "Z": [5.0, 6.0, 7.0, None],
            "yaw": [90.0, 100.0, 110.0, None],
            "pitch": [5.0, 10.0, 15.0, None],
        })

    def parse_event(self, event_name):
        if event_name == "round_start":
            return pd.DataFrame({
                "round": [1, 1, 2, 3],
                "tick": [0, 99, 200, 300],
            })

        if event_name == "round_end":
            return pd.DataFrame({
                "reason": [
                    "t_killed",
                    "ct_killed",
                    "bomb_exploded",
                ],
                "round": [1, 2, 3],
                "tick": [80, 180, 280],
                "winner": ["CT", "T", "T"],
            })

        if event_name == "weapon_fire":
            return pd.DataFrame({
                "tick": [50, 120],
                "user_steamid": [1, 1],
                "user_name": ["PlayerA", "PlayerA"],
                "weapon": ["ak47", "ak47"],
                "silenced": [False, False],
            })

        if event_name == "player_hurt":
            return pd.DataFrame({
                "tick": [130],
                "attacker_steamid": [1],
                "attacker_name": ["PlayerA"],
                "user_steamid": [2],
                "user_name": ["PlayerB"],
                "weapon": ["ak47"],
                "dmg_health": [40],
                "dmg_armor": [5],
                "health": [60],
                "armor": [95],
                "hitgroup": ["chest"],
            })

        if event_name == "player_death":
            return pd.DataFrame({
                "tick": [150],
                "attacker_steamid": [1],
                "attacker_name": ["PlayerA"],
                "user_steamid": [2],
                "user_name": ["PlayerB"],
                "weapon": ["ak47"],
                "headshot": [True],
                "distance": [20.0],
                "hitgroup": ["head"],
                "noscope": [False],
                "penetrated": [0],
                "thrusmoke": [False],
                "attackerblind": [False],
                "attackerinair": [False],
            })

        raise ValueError(f"Unknown event: {event_name}")


def create_parser():
    """
    Create a DemoParser instance without loading a real demo.
    """

    parser = DemoParser.__new__(DemoParser)
    parser.parser = FakeParser()
    parser.match_start_tick = 100

    return parser


def test_get_players():
    parser = create_parser()

    players = parser.get_players()

    assert len(players) == 2

    assert players[0].steamid == 1
    assert players[0].name == "PlayerA"

    assert players[1].steamid == 2
    assert players[1].name == "PlayerB"


def test_get_player_ticks():
    parser = create_parser()

    ticks = parser.get_player_ticks_df()

    # Tick 50 is before the match.
    # Tick 102 contains missing gameplay data.
    assert len(ticks) == 2

    assert ticks.iloc[0]["tick"] == 100
    assert ticks.iloc[1]["tick"] == 101

    assert ticks.isna().sum().sum() == 0


def test_get_rounds():
    parser = create_parser()

    rounds = parser.get_rounds()

    # Prematch round ending at tick 80 must be ignored.
    assert len(rounds) == 2

    assert rounds[0].number == 1
    assert rounds[0].start_tick == 100
    assert rounds[0].end_tick == 180
    assert rounds[0].winner == "T"
    assert rounds[0].reason == "ct_killed"

    assert rounds[1].number == 2
    assert rounds[1].start_tick == 200
    assert rounds[1].end_tick == 280
    assert rounds[1].winner == "T"
    assert rounds[1].reason == "bomb_exploded"


def test_get_shots():
    parser = create_parser()

    shots = parser.get_shots()

    # Shot at tick 50 is before the competitive match.
    assert len(shots) == 1

    assert shots.iloc[0]["tick"] == 120
    assert shots.iloc[0]["user_steamid"] == 1
    assert shots.iloc[0]["weapon"] == "ak47"


def test_get_hits():
    parser = create_parser()

    hits = parser.get_hits()

    assert len(hits) == 1

    hit = hits.iloc[0]

    assert hit["tick"] == 130
    assert hit["attacker_steamid"] == 1
    assert hit["user_steamid"] == 2
    assert hit["weapon"] == "ak47"
    assert hit["dmg_health"] == 40
    assert hit["hitgroup"] == "chest"


def test_get_kills():
    parser = create_parser()

    kills = parser.get_kills()

    assert len(kills) == 1

    kill = kills.iloc[0]

    assert kill["tick"] == 150
    assert kill["attacker_steamid"] == 1
    assert kill["user_steamid"] == 2
    assert kill["weapon"] == "ak47"
    assert bool(kill["headshot"]) is True
    assert kill["hitgroup"] == "head"


def test_get_events():
    parser = create_parser()

    events = parser.get_events()

    assert len(events) == 3

    assert [event.event_type for event in events] == [
        "shot",
        "hit",
        "kill",
    ]

    # Events must be chronologically sorted.
    assert [event.tick for event in events] == [
        120,
        130,
        150,
    ]