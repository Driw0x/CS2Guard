from pathlib import Path
import pandas as pd
from demoparser2 import DemoParser as Demoparser2
from ..models.player import Player
from ..models.round import Round
from ..models.tick import Tick
from ..models.event import Event
from ..models.match import Match


class DemoParser:

    def __init__(self, demo_path: str | Path):
        self.demo_path = Path(demo_path)

        if not self.demo_path.exists():
            raise FileNotFoundError(f'Demo file not found: {self.demo_path}')

        self.parser = Demoparser2(str(self.demo_path))
        self.match_start_tick = self._get_match_start_tick()

    def _get_match_start_tick(self) -> int:
        new_match = self.parser.parse_event('begin_new_match')

        if new_match.empty:
            raise ValueError('Unable to find the beginning of the match.')

        return int(new_match.iloc[-1]['tick'])

    def get_shots(self):
        shots = self.parser.parse_event('weapon_fire')
        shots = shots[shots['tick'] >= self.match_start_tick]
        shots = shots[['tick', 'user_steamid', 'user_name', 'weapon']].dropna()
        shots['tick'] = shots['tick'].astype(int)
        shots['user_steamid'] = shots['user_steamid'].astype(int)
        return shots.reset_index(drop=True)

    def get_hits(self):
        hits = self.parser.parse_event('player_hurt')
        hits = hits[hits['tick'] >= self.match_start_tick]
        return hits[['tick', 'attacker_steamid', 'attacker_name', 'user_steamid', 'user_name', 'weapon', 'dmg_health', 'dmg_armor', 'health', 'armor', 'hitgroup']].dropna(subset=['attacker_steamid', 'user_steamid']).reset_index(drop=True)

    def get_kills(self):
        kills = self.parser.parse_event('player_death')
        kills = kills[kills['tick'] >= self.match_start_tick]
        return kills[['tick', 'attacker_steamid', 'attacker_name', 'user_steamid', 'user_name', 'weapon', 'headshot', 'distance', 'hitgroup', 'noscope', 'penetrated', 'thrusmoke', 'attackerblind', 'attackerinair']].dropna(subset=['user_steamid']).reset_index(drop=True)

    def get_player_ticks_df(self):
        ticks = self.parser.parse_ticks(['X', 'Y', 'Z', 'yaw', 'pitch', 'team_name'])
        ticks = ticks[ticks['tick'] >= self.match_start_tick]
        return ticks[['tick', 'steamid', 'name', 'team_name', 'X', 'Y', 'Z', 'yaw', 'pitch']].dropna().reset_index(drop=True)

    def get_player_ticks(self) -> list[Tick]:
        ticks = self.get_player_ticks_df()
        return [Tick(tick=int(row.tick), steamid=int(row.steamid), player_name=row.name, team=row.team_name, x=float(row.X), y=float(row.Y), z=float(row.Z), yaw=float(row.yaw), pitch=float(row.pitch)) for row in ticks.itertuples(index=False)]

    def get_match_metadata(self) -> dict:
        header = self.parser.parse_header()
        return {'map_name': header.get('map_name'), 'patch_version': header.get('patch_version'), 'demo_version': header.get('demo_version_name')}

    def get_players(self) -> list[Player]:
        ticks = self.parser.parse_ticks(['team_name'])
        players_df = ticks[['steamid', 'name']].dropna(subset=['steamid']).drop_duplicates(subset=['steamid'])
        return [Player(steamid=int(row['steamid']), name=row['name']) for _, row in players_df.iterrows()]

    def get_player_teams(self):
        ticks = self.parser.parse_ticks(['team_name'])
        return ticks[['tick', 'steamid', 'name', 'team_name']].dropna(subset=['steamid']).reset_index(drop=True)

    def get_rounds(self) -> list[Round]:
        starts = self.parser.parse_event('round_start')
        ends = self.parser.parse_event('round_end')
        starts = starts[starts['tick'] > self.match_start_tick].sort_values('tick').reset_index(drop=True)
        ends = ends[ends['tick'] > self.match_start_tick].sort_values('tick').reset_index(drop=True)
        rounds = []

        for index, end in ends.iterrows():
            if index == 0:
                start_tick = self.match_start_tick
            else:
                previous_starts = starts[starts['tick'] < end['tick']]

                if previous_starts.empty:
                    continue

                start_tick = int(previous_starts.iloc[-1]['tick'])

            rounds.append(Round(number=index + 1, start_tick=start_tick, end_tick=int(end['tick']), winner=end['winner'], reason=end['reason']))

        return rounds

    def get_events(self) -> list[Event]:
        events = []
        shots = self.get_shots()

        for row in shots.itertuples(index=False):
            events.append(Event(tick=int(row.tick), event_type='shot', data={'steamid': int(row.user_steamid), 'player_name': row.user_name, 'weapon': row.weapon}))

        hits = self.get_hits()

        for row in hits.itertuples(index=False):
            events.append(Event(tick=int(row.tick), event_type='hit', data={'attacker_steamid': int(row.attacker_steamid), 'attacker_name': row.attacker_name, 'victim_steamid': int(row.user_steamid), 'victim_name': row.user_name, 'weapon': row.weapon, 'damage_health': int(row.dmg_health), 'damage_armor': int(row.dmg_armor), 'hitgroup': row.hitgroup}))

        kills = self.get_kills()

        for row in kills.itertuples(index=False):
            data = {'attacker_steamid': int(row.attacker_steamid) if row.attacker_steamid == row.attacker_steamid else None, 'attacker_name': row.attacker_name, 'victim_steamid': int(row.user_steamid), 'victim_name': row.user_name, 'weapon': row.weapon, 'headshot': bool(row.headshot), 'distance': float(row.distance), 'hitgroup': row.hitgroup, 'noscope': bool(row.noscope), 'penetrated': int(row.penetrated), 'thrusmoke': bool(row.thrusmoke)}
            events.append(Event(tick=int(row.tick), event_type='kill', data=data))

        return sorted(events, key=lambda event: event.tick)

    def get_match(self, include_ticks: bool=False) -> Match:
        metadata = self.get_match_metadata()
        return Match(map_name=metadata['map_name'], patch_version=metadata['patch_version'], demo_version=metadata['demo_version'], players=self.get_players(), rounds=self.get_rounds(), ticks=self.get_player_ticks() if include_ticks else [], events=self.get_events())
