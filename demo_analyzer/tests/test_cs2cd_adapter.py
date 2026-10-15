import json
import pandas as pd
import pytest
from cs2guard_demo.dataset import validate_event_schema, validate_tick_schema
from cs2guard_demo.dataset.adapters import CS2CDAdapter


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


def test_cs2cd_ticks_follow_canonical_schema(tmp_path):
    json_path, parquet_path = create_cs2cd_files(tmp_path)
    fake_ticks = pd.DataFrame({'tick': [100, 100], 'steamid': ['Player_1', 'Player_3'], 'X': [1.0, 2.0], 'Y': [3.0, 4.0], 'Z': [5.0, 6.0], 'yaw': [10.0, 20.0], 'pitch': [1.0, 2.0], 'team_name': ['CT', 'TERRORIST'], 'active_weapon_name': ['M4A1', 'AK-47']})
    fake_ticks.to_parquet(parquet_path, index=False)
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


def test_cs2cd_invalid_ticks_are_dropped(tmp_path):
    json_path, parquet_path = create_cs2cd_files(tmp_path)
    ticks = pd.DataFrame({'tick': [100, 101, 102], 'steamid': ['Player_1'] * 3,
                          'X': [1.0, float('inf'), 1.0], 'Y': [0.0] * 3, 'Z': [0.0] * 3,
                          'yaw': [0.0, 0.0, float('nan')], 'pitch': [0.0] * 3})
    ticks.to_parquet(parquet_path, index=False)
    adapter = CS2CDAdapter(json_path, parquet_path)
    result = adapter.get_ticks()
    assert result['tick'].tolist() == [100]
    assert result['player_id'].tolist() == [f'cs2cd:{adapter.match_id}:Player_1']


def test_cs2cd_missing_files_and_tick_columns_are_rejected(tmp_path):
    with pytest.raises(FileNotFoundError, match='CS2CD JSON file not found'):
        CS2CDAdapter(tmp_path / 'missing.json', tmp_path / 'missing.parquet')
    json_path, parquet_path = create_cs2cd_files(tmp_path)
    with pytest.raises(FileNotFoundError, match='CS2CD Parquet file not found'):
        CS2CDAdapter(json_path, tmp_path / 'missing.parquet')
    pd.DataFrame({'tick': [100]}).to_parquet(parquet_path, index=False)
    with pytest.raises(ValueError, match='Missing CS2CD tick columns'):
        CS2CDAdapter(json_path, parquet_path).get_ticks()


@pytest.mark.parametrize('include_optional', [False, True])
def test_cs2cd_projects_columns_without_changing_ticks(tmp_path, monkeypatch, include_optional):
    json_path, parquet_path = create_cs2cd_files(tmp_path)
    data = pd.DataFrame({
        'unused': ['ignored'] * 6,
        'tick': pd.Series([100, 101, 102, 103, 104, 105], dtype='int32'),
        'steamid': ['Player_1', 'Player_3', 'Player_1', 'Player_1', None, 'Player_3'],
        'X': pd.Series([1.0, 2.0, float('inf'), 1.0, 1.0, 1.0], dtype='float32'),
        'Y': [3.0, 4.0, 0.0, 0.0, 0.0, 0.0],
        'Z': [5.0, 6.0, 0.0, 0.0, 0.0, 0.0],
        'yaw': [10.0, 20.0, 0.0, float('nan'), 0.0, 0.0],
        'pitch': [1.0, 2.0, 0.0, 0.0, 0.0, float('-inf')],
    })
    expected_optional = {
        'team_name': ['CT', 'TERRORIST'], 'weapon': ['M4A1', 'AK-47'],
        'health': [100.0, float('nan')], 'armor_value': [90, 80],
        'is_alive': [True, True], 'is_airborne': [False, True],
        'velocity_X': [1.0, 2.0], 'velocity_Y': [3.0, 4.0], 'velocity_Z': [5.0, 6.0],
    }
    selected_columns = ['tick', 'steamid', 'X', 'Y', 'Z', 'yaw', 'pitch']
    if include_optional:
        for name, values in expected_optional.items():
            column = 'active_weapon_name' if name == 'weapon' else name
            data[column] = values + values + values
            selected_columns.append(column)
        data.loc[1, 'health'] = float('-inf')
    data.index = range(20, 26)
    data.to_parquet(parquet_path)
    read_parquet = pd.read_parquet
    calls = []

    def projected_read(path, *, columns):
        calls.append(columns)
        return read_parquet(path, columns=columns)

    monkeypatch.setattr(pd, 'read_parquet', projected_read)
    adapter = CS2CDAdapter(json_path, parquet_path)
    result = adapter.get_ticks()
    expected = pd.DataFrame({
        'source': ['cs2cd'] * 2, 'match_id': [adapter.match_id] * 2,
        'player_id': [f'cs2cd:{adapter.match_id}:Player_1', f'cs2cd:{adapter.match_id}:Player_3'],
        'source_player_id': ['Player_1', 'Player_3'], 'identity_scope': ['match'] * 2,
        'label': ['legitimate', 'suspicious'], 'tick': pd.Series([100, 101], dtype='int32'),
        'x': pd.Series([1.0, 2.0], dtype='float32'), 'y': [3.0, 4.0], 'z': [5.0, 6.0],
        'yaw': [10.0, 20.0], 'pitch': [1.0, 2.0],
        **(expected_optional if include_optional else {}),
    })
    assert calls == [selected_columns]
    pd.testing.assert_frame_equal(result, expected, check_exact=True)


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
