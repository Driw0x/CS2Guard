import importlib.util
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def build_script(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'build_dataset.py'
    spec = importlib.util.spec_from_file_location('build_dataset_script', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'OUTPUT_DIRECTORY', tmp_path)
    monkeypatch.setattr(module, 'CHECKPOINT_FILE', tmp_path / '.build_checkpoint.json')
    return module


@pytest.mark.parametrize('name', ['events', 'ticks'])
def test_csv_chunks_keep_source_columns_aligned(build_script, name):
    first = pd.DataFrame([{'source': 'demo', 'match_id': 'first', 'player_id': 'demo:1',
                           'tick': 100, 'player_name': 'Player', 'weapon': 'ak47'}])
    second = pd.DataFrame([{'weapon': 'deagle', 'tick': 200, 'player_id': 'cs2cd:second:Player_1',
                            'match_id': 'second', 'source': 'cs2cd',
                            ('attacker_blind' if name == 'events' else 'velocity_X'): 1.0}])
    build_script.append_dataframe(name, first)
    build_script.append_dataframe(name, second)
    result = pd.read_csv(build_script.output_path(name))
    assert list(result.columns) == build_script.OUTPUT_COLUMNS[name]
    assert result['tick'].tolist() == [100, 200]
    assert result['weapon'].tolist() == ['ak47', 'deagle']
    assert result['match_id'].tolist() == ['first', 'second']
    assert result.loc[0, 'player_name'] == 'Player'
    assert pd.isna(result.loc[1, 'player_name'])


def test_empty_chunk_does_not_hide_later_header(build_script):
    build_script.append_dataframe('features', pd.DataFrame())
    assert not build_script.output_path('features').exists()
    features = pd.DataFrame([{'window_id': 'w', 'mean_angular_speed': 64.0}])
    build_script.append_dataframe('features', features)
    pd.testing.assert_frame_equal(pd.read_csv(build_script.output_path('features')), features)


def test_resume_rolls_back_only_interrupted_rows(build_script):
    first = pd.DataFrame([{'window_id': 'first', 'mean_angular_speed': 64.0}])
    build_script.append_dataframe('features', first)
    path = build_script.output_path('features')
    original_bytes = path.read_bytes()
    checkpoint = build_script.empty_checkpoint()
    checkpoint['completed'] = ['demo:first.dem']
    checkpoint['current'] = {'source_key': 'demo:second.dem', 'file_sizes': build_script.get_output_sizes()}
    build_script.save_checkpoint(checkpoint)
    build_script.append_dataframe('features', pd.DataFrame([{'window_id': 'second', 'mean_angular_speed': 128.0}]))
    build_script.rollback_current(checkpoint)
    assert path.read_bytes() == original_bytes
    assert build_script.load_checkpoint()['current'] is None
    assert build_script.load_checkpoint()['completed'] == ['demo:first.dem']


def test_incompatible_resume_header_fails_before_append(build_script):
    path = build_script.output_path('events')
    path.write_text('tick,player_id\n100,demo:1\n', encoding='utf-8')
    original_bytes = path.read_bytes()
    with pytest.raises(ValueError, match='Incompatible existing events CSV header'):
        build_script.append_dataframe('events', pd.DataFrame([{'tick': 200, 'player_id': 'demo:2'}]))
    assert path.read_bytes() == original_bytes


def test_unknown_source_column_is_not_silently_discarded(build_script):
    with pytest.raises(ValueError, match='Unsupported ticks output columns'):
        build_script.append_dataframe('ticks', pd.DataFrame([{'tick': 100, 'new_sensor': 1.0}]))
    assert not build_script.output_path('ticks').exists()
