import pandas as pd
import pytest
from cs2guard_demo.dataset.schema import build_player_id, validate_event_schema, validate_tick_schema


def test_global_player_id_is_stable_between_matches():
    first = build_player_id(source='demo', match_id='match_a', source_player_id='76561198000000001', identity_scope='global')
    second = build_player_id(source='demo', match_id='match_b', source_player_id='76561198000000001', identity_scope='global')
    assert first == second
    assert first == 'demo:76561198000000001'


def test_match_scoped_player_id_is_unique_between_matches():
    first = build_player_id(source='cs2cd', match_id='match_a', source_player_id='Player_3', identity_scope='match')
    second = build_player_id(source='cs2cd', match_id='match_b', source_player_id='Player_3', identity_scope='match')
    assert first != second
    assert first == 'cs2cd:match_a:Player_3'
    assert second == 'cs2cd:match_b:Player_3'


def test_event_schema_accepts_extra_m1_columns():
    dataset = pd.DataFrame({'source': ['cs2cd'], 'match_id': ['match_a'], 'player_id': ['cs2cd:match_a:Player_3'], 'source_player_id': ['Player_3'], 'identity_scope': ['match'], 'label': ['suspicious'], 'tick': [100], 'event_type': ['kill'], 'weapon': ['ak47'], 'victim_id': ['cs2cd:match_a:Player_7'], 'headshot': [True], 'distance': [500.0]})
    validate_event_schema(dataset)


def test_tick_schema_accepts_extra_m1_columns():
    dataset = pd.DataFrame({'source': ['cs2cd'], 'match_id': ['match_a'], 'player_id': ['cs2cd:match_a:Player_3'], 'source_player_id': ['Player_3'], 'identity_scope': ['match'], 'label': ['suspicious'], 'tick': [100], 'x': [10.0], 'y': [20.0], 'z': [30.0], 'yaw': [90.0], 'pitch': [5.0], 'weapon': ['ak47'], 'health': [100], 'team_name': ['TERRORIST']})
    validate_tick_schema(dataset)


def test_schema_accepts_unlabeled_data():
    dataset = pd.DataFrame({'source': ['demo'], 'match_id': ['match_a'], 'player_id': ['demo:76561198000000001'], 'source_player_id': ['76561198000000001'], 'identity_scope': ['global'], 'label': [pd.NA], 'tick': [100], 'event_type': ['shot']})
    validate_event_schema(dataset)


def test_schema_rejects_missing_required_column():
    dataset = pd.DataFrame({'source': ['cs2cd'], 'match_id': ['match_a']})

    with pytest.raises(ValueError, match='Missing canonical columns'):
        validate_event_schema(dataset)


def test_schema_rejects_invalid_identity_scope():
    with pytest.raises(ValueError, match='Invalid identity scope'):
        build_player_id(source='cs2cd', match_id='match_a', source_player_id='Player_3', identity_scope='unknown')


def test_schema_rejects_invalid_label():
    dataset = pd.DataFrame({'source': ['cs2cd'], 'match_id': ['match_a'], 'player_id': ['cs2cd:match_a:Player_3'], 'source_player_id': ['Player_3'], 'identity_scope': ['match'], 'label': ['cheater'], 'tick': [100], 'event_type': ['shot']})

    with pytest.raises(ValueError, match='Invalid labels'):
        validate_event_schema(dataset)
