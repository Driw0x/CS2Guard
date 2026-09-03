import pandas as pd
SCHEMA_VERSION = '1.0'
VALID_IDENTITY_SCOPES = {'global', 'match'}
VALID_LABELS = {'legitimate', 'suspicious'}
IDENTITY_COLUMNS = ['source', 'match_id', 'player_id', 'source_player_id', 'identity_scope', 'label']
EVENT_COLUMNS = IDENTITY_COLUMNS + ['tick', 'event_type']
TICK_COLUMNS = IDENTITY_COLUMNS + ['tick', 'x', 'y', 'z', 'yaw', 'pitch']
AIM_FEATURE_COLUMNS = IDENTITY_COLUMNS + ['window_id', 'shot_tick', 'mean_angular_speed', 'max_angular_speed', 'std_angular_speed', 'mean_angular_acceleration', 'max_angular_acceleration', 'std_angular_acceleration']


def build_player_id(source: str, match_id: str, source_player_id: str, identity_scope: str) -> str:
    source = _require_string(source, 'source')
    match_id = _require_string(match_id, 'match_id')
    source_player_id = _require_string(source_player_id, 'source_player_id')

    if identity_scope not in VALID_IDENTITY_SCOPES:
        raise ValueError(f'Invalid identity scope: {identity_scope}')

    if identity_scope == 'global':
        return f'{source}:{source_player_id}'

    return f'{source}:{match_id}:{source_player_id}'


def validate_event_schema(dataset: pd.DataFrame) -> None:
    _validate_dataset(dataset, EVENT_COLUMNS)


def validate_tick_schema(dataset: pd.DataFrame) -> None:
    _validate_dataset(dataset, TICK_COLUMNS)


def validate_aim_feature_schema(dataset: pd.DataFrame) -> None:
    _validate_dataset(dataset, AIM_FEATURE_COLUMNS)


def _validate_dataset(dataset: pd.DataFrame, required_columns: list[str]) -> None:
    missing_columns = [column for column in required_columns if column not in dataset.columns]

    if missing_columns:
        raise ValueError(f'Missing canonical columns: {missing_columns}')

    if dataset.empty:
        return

    required_identity_columns = ['source', 'match_id', 'player_id', 'source_player_id', 'identity_scope']

    for column in required_identity_columns:
        if dataset[column].isna().any():
            raise ValueError(f"Canonical column '{column}' cannot contain missing values.")

    invalid_scopes = set(dataset['identity_scope'].dropna()) - VALID_IDENTITY_SCOPES

    if invalid_scopes:
        raise ValueError(f'Invalid identity scopes: {sorted(invalid_scopes)}')

    invalid_labels = set(dataset['label'].dropna()) - VALID_LABELS

    if invalid_labels:
        raise ValueError(f'Invalid labels: {sorted(invalid_labels)}')


def _require_string(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a non-empty string.')

    return value.strip()
