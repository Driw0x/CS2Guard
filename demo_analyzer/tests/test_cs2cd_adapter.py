import json
import pandas as pd
from cs2guard_demo.dataset.adapters.cs2cd import CS2CDAdapter
from cs2guard_demo.dataset.schema import validate_event_schema, validate_tick_schema


def create_cs2cd_files(tmp_path):
    json_path = tmp_path / 'match.json'
    parquet_path = tmp_path / 'match.parquet'
    data = {'weapon_fire': [{'tick': 100, 'user_steamid': 'Player_1', 'weapon': 'ak47'}, {'tick': 110, 'user_steamid': 'Player_3', 'weapon': 'deagle'}], 'player_hurt': [{'tick': 120, 'attacker_steamid': 'Player_3', 'user_steamid': 'Player_2', 'weapon': 'deagle', 'dmg_health': 50, 'dmg_armor': 10, 'health': 50, 'armor': 90, 'hitgroup': 'chest'}], 'player_death': [{'tick': 130, 'attacker_steamid': 'Player_3', 'user_steamid': 'Player_2', 'weapon': 'deagle', 'dmg_health': 50, 'dmg_armor': 0, 'headshot': True, 'hitgroup': 'head', 'distance': 500.0, 'noscope': False, 'penetrated': 0, 'thrusmoke': False, 'attackerblind': False, 'attackerinair': False}], 'cheaters': [{'steamid': 'Player_3'}], 'CSstats_info': [{'map': 'de_mirage', 'server': 'eu_north Server', 'avg_rank': 'Gold Nova Master', 'match_making_type': 'Official Matchmaking'}]}
    json_path.write_text(json.dumps(data), encoding='utf-8')
    parquet_path.touch()
    return (json_path, parquet_path)


def test_cs2cd_metadata(tmp_path):
    json_path, parquet_path = create_cs2cd_files(tmp_path)
    adapter = CS2CDAdapter(json_path, parquet_path)
    metadata = adapter.get_metadata()
    assert metadata['source'] == 'cs2cd'
    assert metadata['map_name'] == 'de_mirage'
    assert metadata['identity_scope'] == 'match'


def test_cs2cd_labels(tmp_path):
    json_path, parquet_path = create_cs2cd_files(tmp_path)
    adapter = CS2CDAdapter(json_path, parquet_path)
    labels = adapter.get_labels()
    player_3 = labels[labels['source_player_id'] == 'Player_3'].iloc[0]
    player_1 = labels[labels['source_player_id'] == 'Player_1'].iloc[0]
    assert player_3['label'] == 'suspicious'
    assert player_1['label'] == 'legitimate'
    assert player_3['player_id'] == f'cs2cd:{adapter.match_id}:Player_3'
    assert player_1['player_id'] == f'cs2cd:{adapter.match_id}:Player_1'


def test_cs2cd_events_follow_canonical_schema(tmp_path):
    json_path, parquet_path = create_cs2cd_files(tmp_path)
    adapter = CS2CDAdapter(json_path, parquet_path)
    events = adapter.get_events()
    validate_event_schema(events)
    assert len(events) == 4
    assert set(events['event_type']) == {'shot', 'hit', 'kill'}
    suspicious_events = events[events['source_player_id'] == 'Player_3']
    assert (suspicious_events['label'] == 'suspicious').all()


def test_cs2cd_ticks_follow_canonical_schema(tmp_path, monkeypatch):
    json_path, parquet_path = create_cs2cd_files(tmp_path)
    fake_ticks = pd.DataFrame({'tick': [100, 100], 'steamid': ['Player_1', 'Player_3'], 'X': [1.0, 2.0], 'Y': [3.0, 4.0], 'Z': [5.0, 6.0], 'yaw': [10.0, 20.0], 'pitch': [1.0, 2.0], 'team_name': ['CT', 'TERRORIST'], 'active_weapon_name': ['M4A1', 'AK-47']})
    monkeypatch.setattr(pd, 'read_parquet', lambda _: fake_ticks)
    adapter = CS2CDAdapter(json_path, parquet_path)
    ticks = adapter.get_ticks()
    validate_tick_schema(ticks)
    assert len(ticks) == 2
    assert 'steamid' not in ticks.columns
    assert 'weapon' in ticks.columns
    player_3 = ticks[ticks['source_player_id'] == 'Player_3'].iloc[0]
    assert player_3['label'] == 'suspicious'
    assert player_3['identity_scope'] == 'match'
    assert player_3['player_id'] == f'cs2cd:{adapter.match_id}:Player_3'


def test_same_anonymous_player_is_unique_between_matches(tmp_path):
    first_directory = tmp_path / 'first'
    second_directory = tmp_path / 'second'
    first_directory.mkdir()
    second_directory.mkdir()
    first_json, first_parquet = create_cs2cd_files(first_directory)
    second_json, second_parquet = create_cs2cd_files(second_directory)
    second_data = json.loads(second_json.read_text(encoding='utf-8'))
    second_data['weapon_fire'].append({'tick': 999, 'user_steamid': 'Player_2', 'weapon': 'ak47'})
    second_json.write_text(json.dumps(second_data), encoding='utf-8')
    first_adapter = CS2CDAdapter(first_json, first_parquet)
    second_adapter = CS2CDAdapter(second_json, second_parquet)
    first_player = first_adapter._canonical_player_id('Player_3')
    second_player = second_adapter._canonical_player_id('Player_3')
    assert first_adapter.match_id != second_adapter.match_id
    assert first_player != second_player


def test_same_anonymous_id_can_have_different_labels_between_matches(tmp_path):
    first_directory = tmp_path / 'first'
    second_directory = tmp_path / 'second'
    first_directory.mkdir()
    second_directory.mkdir()
    first_json, first_parquet = create_cs2cd_files(first_directory)
    second_json, second_parquet = create_cs2cd_files(second_directory)
    second_data = json.loads(second_json.read_text(encoding='utf-8'))
    second_data['cheaters'] = [{'steamid': 'Player_2'}]
    second_data['weapon_fire'].append({'tick': 999, 'user_steamid': 'Player_2', 'weapon': 'ak47'})
    second_json.write_text(json.dumps(second_data), encoding='utf-8')
    first_adapter = CS2CDAdapter(first_json, first_parquet)
    second_adapter = CS2CDAdapter(second_json, second_parquet)
    first_labels = first_adapter.get_labels()
    second_labels = second_adapter.get_labels()
    first_player_3 = first_labels[first_labels['source_player_id'] == 'Player_3'].iloc[0]
    second_player_3 = second_labels[second_labels['source_player_id'] == 'Player_3'].iloc[0]
    assert first_player_3['label'] == 'suspicious'
    assert second_player_3['label'] == 'legitimate'
    assert first_player_3['player_id'] != second_player_3['player_id']
