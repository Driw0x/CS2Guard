from pathlib import Path
import pandas as pd

from cs2guard_demo.dataset.builder import is_ignored_weapon, is_valid_player, safe_bool, safe_float, safe_int
from cs2guard_demo.dataset.schema import build_player_id, validate_event_schema, validate_tick_schema
from cs2guard_demo.parser.demo_parser import DemoParser

SOURCE = "demo"
IDENTITY_SCOPE = "global"


class DemoAdapter:

    def __init__(self, demo_path: str | Path):
        self.demo_path = Path(demo_path)

        if not self.demo_path.exists():
            raise FileNotFoundError(f"Demo file not found: {self.demo_path}")

        self.parser = DemoParser(self.demo_path)
        self.match_id = self.demo_path.stem
        self.metadata = self.parser.get_match_metadata()

    def _canonical_player_id(self, source_player_id: str) -> str:
        return build_player_id(source=SOURCE, match_id=self.match_id, source_player_id=source_player_id, identity_scope=IDENTITY_SCOPE)

    def get_metadata(self) -> dict:
        return {
            "source": SOURCE,
            "match_id": self.match_id,
            "map_name": self.metadata.get("map_name"),
            "patch_version": self.metadata.get("patch_version"),
            "demo_version": self.metadata.get("demo_version"),
            "identity_scope": IDENTITY_SCOPE,
        }

    def get_ticks(self) -> pd.DataFrame:
        ticks = self.parser.get_player_ticks_df().copy()
        ticks = ticks.replace([float("inf"), float("-inf")], pd.NA)
        ticks = ticks.dropna(subset=["tick", "steamid", "X", "Y", "Z", "yaw", "pitch"])

        if ticks.empty:
            return pd.DataFrame(columns=["source", "match_id", "player_id", "source_player_id", "identity_scope", "label", "tick", "x", "y", "z", "yaw", "pitch"])

        ticks = ticks[ticks.apply(lambda row: is_valid_player(row["steamid"], row["name"]), axis=1)].copy()
        ticks["source_player_id"] = ticks["steamid"].map(lambda value: str(int(value)))
        ticks["player_id"] = ticks["source_player_id"].map(self._canonical_player_id)
        ticks["source"] = SOURCE
        ticks["match_id"] = self.match_id
        ticks["identity_scope"] = IDENTITY_SCOPE
        ticks["label"] = None
        ticks = ticks.drop(columns="steamid")
        ticks = ticks.rename(columns={"X": "x", "Y": "y", "Z": "z", "name": "player_name"})

        base_columns = ["source", "match_id", "player_id", "source_player_id", "identity_scope", "label", "tick", "x", "y", "z", "yaw", "pitch"]
        remaining_columns = [column for column in ticks.columns if column not in base_columns]
        ticks = ticks[base_columns + remaining_columns].reset_index(drop=True)

        validate_tick_schema(ticks)
        return ticks

    def get_events(self) -> pd.DataFrame:
        rows = []
        rows.extend(self._normalize_shots())
        rows.extend(self._normalize_hits())
        rows.extend(self._normalize_kills())

        if not rows:
            return pd.DataFrame(columns=["source", "match_id", "player_id", "source_player_id", "identity_scope", "label", "tick", "event_type"])

        events = pd.DataFrame(rows)
        events = events.sort_values(["tick", "event_type"]).reset_index(drop=True)

        validate_event_schema(events)
        return events

    def _base_event(self, event_type: str, tick: int, steamid: int, player_name: str) -> dict:
        source_player_id = str(steamid)

        return {
            "source": SOURCE,
            "match_id": self.match_id,
            "player_id": self._canonical_player_id(source_player_id),
            "source_player_id": source_player_id,
            "identity_scope": IDENTITY_SCOPE,
            "label": None,
            "tick": tick,
            "event_type": event_type,
            "player_name": player_name,
            "map_name": self.metadata.get("map_name"),
            "patch_version": self.metadata.get("patch_version"),
            "demo_version": self.metadata.get("demo_version"),
        }

    def _normalize_shots(self) -> list[dict]:
        rows = []

        for shot in self.parser.get_shots().itertuples(index=False):
            tick = safe_int(shot.tick)
            steamid = safe_int(shot.user_steamid)

            if tick is None or not is_valid_player(steamid, shot.user_name):
                continue

            if is_ignored_weapon(shot.weapon):
                continue

            row = self._base_event("shot", tick, steamid, shot.user_name)
            row["weapon"] = shot.weapon.strip()
            rows.append(row)

        return rows

    def _normalize_hits(self) -> list[dict]:
        rows = []

        for hit in self.parser.get_hits().itertuples(index=False):
            tick = safe_int(hit.tick)
            attacker = safe_int(hit.attacker_steamid)
            victim = safe_int(hit.user_steamid)

            if tick is None or not is_valid_player(attacker, hit.attacker_name):
                continue

            if victim is None or victim <= 0 or attacker == victim:
                continue

            if is_ignored_weapon(hit.weapon):
                continue

            victim_source_player_id = str(victim)
            row = self._base_event("hit", tick, attacker, hit.attacker_name)
            row.update({
                "victim_id": self._canonical_player_id(victim_source_player_id),
                "victim_source_player_id": victim_source_player_id,
                "victim_name": hit.user_name,
                "weapon": hit.weapon.strip(),
                "damage_health": safe_int(hit.dmg_health),
                "damage_armor": safe_int(hit.dmg_armor),
                "victim_health": safe_int(hit.health),
                "victim_armor": safe_int(hit.armor),
                "hitgroup": hit.hitgroup if isinstance(hit.hitgroup, str) else None,
            })
            rows.append(row)

        return rows

    def _normalize_kills(self) -> list[dict]:
        rows = []

        for kill in self.parser.get_kills().itertuples(index=False):
            tick = safe_int(kill.tick)
            attacker = safe_int(kill.attacker_steamid)
            victim = safe_int(kill.user_steamid)

            if tick is None or not is_valid_player(attacker, kill.attacker_name):
                continue

            if victim is None or victim <= 0 or attacker == victim:
                continue

            if is_ignored_weapon(kill.weapon):
                continue

            victim_source_player_id = str(victim)
            row = self._base_event("kill", tick, attacker, kill.attacker_name)
            row.update({
                "victim_id": self._canonical_player_id(victim_source_player_id),
                "victim_source_player_id": victim_source_player_id,
                "victim_name": kill.user_name,
                "weapon": kill.weapon.strip(),
                "headshot": safe_bool(kill.headshot),
                "distance": safe_float(kill.distance),
                "hitgroup": kill.hitgroup if isinstance(kill.hitgroup, str) else None,
                "noscope": safe_bool(kill.noscope),
                "penetrated": safe_int(kill.penetrated),
                "thrusmoke": safe_bool(kill.thrusmoke),
            })
            rows.append(row)

        return rows