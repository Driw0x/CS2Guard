import math
import pandas as pd
from .normalization import AIM_FEATURE_COLUMNS


def _finite_numeric_stats(dataset: pd.DataFrame, columns: list[str]) -> dict:
    stats = {}

    for column in columns:
        if column not in dataset.columns:
            continue

        values = pd.to_numeric(dataset[column], errors='coerce').dropna()

        if values.empty:
            continue

        finite_values = values[values.map(math.isfinite)]

        if finite_values.empty:
            continue

        stats[column] = {'mean': float(finite_values.mean()), 'std': float(finite_values.std(ddof=0)), 'min': float(finite_values.min()), 'max': float(finite_values.max())}

    return stats


def generate_dataset_statistics(event_dataset: pd.DataFrame, player_dataset: pd.DataFrame, temporal_windows: pd.DataFrame, aim_features: pd.DataFrame) -> dict:
    event_player_column = 'player_id' if 'player_id' in event_dataset else 'steamid'
    player_column = 'player_id' if 'player_id' in player_dataset else 'steamid'
    feature_player_column = 'player_id' if 'player_id' in aim_features else 'steamid'
    statistics = {'events': {'samples': len(event_dataset), 'matches': event_dataset['match_id'].nunique() if 'match_id' in event_dataset else 0, 'players': event_dataset[event_player_column].nunique() if event_player_column in event_dataset else 0, 'event_types': event_dataset['event_type'].value_counts().to_dict() if 'event_type' in event_dataset else {}}, 'players': {'samples': len(player_dataset), 'unique_players': player_dataset[player_column].nunique() if player_column in player_dataset else 0}, 'temporal_windows': {'windows': temporal_windows['window_id'].nunique() if 'window_id' in temporal_windows else 0, 'rows': len(temporal_windows)}, 'aim_features': {'samples': len(aim_features), 'matches': aim_features['match_id'].nunique() if 'match_id' in aim_features else 0, 'players': aim_features[feature_player_column].nunique() if feature_player_column in aim_features else 0}}
    statistics['aim_features']['numerical'] = _finite_numeric_stats(aim_features, AIM_FEATURE_COLUMNS)

    if 'label' in aim_features.columns:
        statistics['aim_features']['labels'] = aim_features['label'].value_counts(dropna=False).to_dict()

    if 'split' in aim_features.columns:
        statistics['aim_features']['splits'] = aim_features['split'].value_counts(dropna=False).to_dict()

    statistics['missing_values'] = {'events': int(event_dataset.isna().sum().sum()), 'players': int(player_dataset.isna().sum().sum()), 'temporal_windows': int(temporal_windows.isna().sum().sum()), 'aim_features': int(aim_features.isna().sum().sum())}
    return statistics
