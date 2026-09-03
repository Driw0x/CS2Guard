import hashlib
import json
from pathlib import Path
import pandas as pd
from cs2guard_demo.dataset.schema import build_player_id, validate_event_schema, validate_tick_schema
SOURCE = 'cs2cd'
IDENTITY_SCOPE = 'match'
REQUIRED_TICK_COLUMNS = {'tick', 'steamid', 'X', 'Y', 'Z', 'yaw', 'pitch'}


class CS2CDAdapter:

    def __init__(self, json_path: str | Path, parquet_path: str | Path):
        self.json_path = Path(json_path)
        self.parquet_path = Path(parquet_path)

        if not self.json_path.exists():
            raise FileNotFoundError(f'CS2CD JSON file not found: {self.json_path}')

        if not self.parquet_path.exists():
            raise FileNotFoundError(f'CS2CD Parquet file not found: {self.parquet_path}')

        with self.json_path.open('r', encoding='utf-8') as file:
            self.events = json.load(file)

        self.match_id = self._build_match_id()
        self.cheaters = self._load_cheaters()

    def _build_match_id(self) -> str:
        digest = hashlib.sha256(self.json_path.read_bytes()).hexdigest()[:16]
        return f'cs2cd_{digest}'

    def _load_cheaters(self) -> set[str]:
        cheaters = self.events.get('cheaters', [])
        return {str(entry['steamid']) for entry in cheaters if isinstance(entry, dict) and entry.get('steamid')}

    def _canonical_player_id(self, source_player_id: str) -> str:
        return build_player_id(source=SOURCE, match_id=self.match_id, source_player_id=source_player_id, identity_scope=IDENTITY_SCOPE)

    def _player_label(self, source_player_id: str) -> str:
        return 'suspicious' if source_player_id in self.cheaters else 'legitimate'

    def get_metadata(self) -> dict:
        csstats_info = self.events.get('CSstats_info', [])
        info = csstats_info[0] if csstats_info else {}
        return {'source': SOURCE, 'match_id': self.match_id, 'map_name': info.get('map'), 'server': info.get('server'), 'avg_rank': info.get('avg_rank'), 'matchmaking_type': info.get('match_making_type'), 'identity_scope': IDENTITY_SCOPE}

    def get_labels(self) -> pd.DataFrame:
        player_ids = self._collect_source_player_ids()
        rows = []

        for source_player_id in sorted(player_ids):
            rows.append({'source': SOURCE, 'match_id': self.match_id, 'player_id': self._canonical_player_id(source_player_id), 'source_player_id': source_player_id, 'identity_scope': IDENTITY_SCOPE, 'label': self._player_label(source_player_id)})

        return pd.DataFrame(rows)

    def _collect_source_player_ids(self) -> set[str]:
        players = set()

        for event_name, event_rows in self.events.items():
            if event_name in {'cheaters', 'CSstats_info'} or not isinstance(event_rows, list):
                continue

            for row in event_rows:
                if not isinstance(row, dict):
                    continue

                for field in ('user_steamid', 'attacker_steamid', 'assister_steamid', 'victim_steamid'):
                    value = row.get(field)

                    if isinstance(value, str) and value.startswith('Player_'):
                        players.add(value)

        players.update(self.cheaters)
        return players

    def get_ticks(self) -> pd.DataFrame:
        ticks = pd.read_parquet(self.parquet_path)
        missing_columns = REQUIRED_TICK_COLUMNS - set(ticks.columns)

        if missing_columns:
            raise ValueError(f'Missing CS2CD tick columns: {sorted(missing_columns)}')

        optional_columns = ['team_name', 'active_weapon_name', 'health', 'armor_value', 'is_alive', 'is_airborne', 'velocity_X', 'velocity_Y', 'velocity_Z']
        selected_columns = ['tick', 'steamid', 'X', 'Y', 'Z', 'yaw', 'pitch']

        for column in optional_columns:
            if column in ticks.columns:
                selected_columns.append(column)

        ticks = ticks[selected_columns].copy()
        ticks = ticks.dropna(subset=['tick', 'steamid', 'X', 'Y', 'Z', 'yaw', 'pitch'])
        ticks['source_player_id'] = ticks['steamid'].astype(str)
        ticks['player_id'] = ticks['source_player_id'].map(self._canonical_player_id)
        ticks['source'] = SOURCE
        ticks['match_id'] = self.match_id
        ticks['identity_scope'] = IDENTITY_SCOPE
        ticks['label'] = ticks['source_player_id'].map(self._player_label)
        ticks = ticks.drop(columns='steamid')
        ticks = ticks.rename(columns={'X': 'x', 'Y': 'y', 'Z': 'z', 'active_weapon_name': 'weapon'})
        base_columns = ['source', 'match_id', 'player_id', 'source_player_id', 'identity_scope', 'label', 'tick', 'x', 'y', 'z', 'yaw', 'pitch']
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
            return pd.DataFrame(columns=['source', 'match_id', 'player_id', 'source_player_id', 'identity_scope', 'label', 'tick', 'event_type'])

        events = pd.DataFrame(rows)
        events = events.sort_values(['tick', 'event_type']).reset_index(drop=True)
        validate_event_schema(events)
        return events

    def _base_event(self, event_type: str, tick: int, source_player_id: str) -> dict:
        return {'source': SOURCE, 'match_id': self.match_id, 'player_id': self._canonical_player_id(source_player_id), 'source_player_id': source_player_id, 'identity_scope': IDENTITY_SCOPE, 'label': self._player_label(source_player_id), 'tick': int(tick), 'event_type': event_type}

    def _normalize_shots(self) -> list[dict]:
        rows = []

        for event in self.events.get('weapon_fire', []):
            source_player_id = event.get('user_steamid')
            tick = event.get('tick')

            if not source_player_id or tick is None:
                continue

            row = self._base_event('shot', tick, source_player_id)
            row['weapon'] = event.get('weapon')
            rows.append(row)

        return rows

    def _normalize_hits(self) -> list[dict]:
        rows = []

        for event in self.events.get('player_hurt', []):
            attacker = event.get('attacker_steamid')
            victim = event.get('user_steamid')
            tick = event.get('tick')

            if not attacker or not victim or tick is None:
                continue

            if attacker == victim:
                continue

            row = self._base_event('hit', tick, attacker)
            row.update({'victim_id': self._canonical_player_id(victim), 'victim_source_player_id': victim, 'weapon': event.get('weapon'), 'damage_health': event.get('dmg_health'), 'damage_armor': event.get('dmg_armor'), 'victim_health': event.get('health'), 'victim_armor': event.get('armor'), 'hitgroup': event.get('hitgroup')})
            rows.append(row)

        return rows

    def _normalize_kills(self) -> list[dict]:
        rows = []

        for event in self.events.get('player_death', []):
            attacker = event.get('attacker_steamid')
            victim = event.get('user_steamid')
            tick = event.get('tick')

            if not attacker or not victim or tick is None:
                continue

            if attacker == victim:
                continue

            row = self._base_event('kill', tick, attacker)
            row.update({'victim_id': self._canonical_player_id(victim), 'victim_source_player_id': victim, 'weapon': event.get('weapon'), 'damage_health': event.get('dmg_health'), 'damage_armor': event.get('dmg_armor'), 'hitgroup': event.get('hitgroup'), 'headshot': event.get('headshot'), 'distance': event.get('distance'), 'noscope': event.get('noscope'), 'penetrated': event.get('penetrated'), 'thrusmoke': event.get('thrusmoke'), 'attacker_blind': event.get('attackerblind'), 'attacker_in_air': event.get('attackerinair')})
            rows.append(row)

        return rows
