import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

FEATURE_COLUMNS = [
    "mean_angular_speed",
    "max_angular_speed",
    "std_angular_speed",
    "mean_angular_acceleration",
    "max_angular_acceleration",
    "std_angular_acceleration",
]

PLAYER_GROUP_COLUMNS = [
    "source",
    "match_id",
    "player_id",
    "source_player_id",
    "identity_scope",
    "label",
]


def prepare_features(
    df: pd.DataFrame,
    feature_columns: list[str] | None = None,
) -> pd.DataFrame:
    columns = FEATURE_COLUMNS if feature_columns is None else feature_columns
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")

    features = df[columns].astype(float)

    if not np.isfinite(features.to_numpy()).all():
        raise ValueError("Feature columns contain NaN or infinite values")

    return features


def aggregate_player_scores(df: pd.DataFrame) -> pd.DataFrame:
    missing = [column for column in PLAYER_GROUP_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing player columns: {missing}")

    return (
        df.groupby(PLAYER_GROUP_COLUMNS, dropna=False)
        .agg(
            window_count=("window_id", "size"),
            mean_anomaly_score=("anomaly_score", "mean"),
            max_anomaly_score=("anomaly_score", "max"),
            anomalous_window_ratio=("is_anomaly", "mean"),
        )
        .reset_index()
    )


def compute_suspicion_scores(df: pd.DataFrame) -> pd.DataFrame:
    required = ["mean_anomaly_score", "label"]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"Missing suspicion score columns: {missing}")

    if not np.isfinite(df["mean_anomaly_score"].to_numpy()).all():
        raise ValueError("Mean anomaly scores contain NaN or infinite values")

    legitimate = np.sort(
        df.loc[df["label"] == "legitimate", "mean_anomaly_score"].to_numpy()
    )

    if len(legitimate) == 0:
        raise ValueError("No legitimate players available for calibration")

    scored = df.copy()
    scores = scored["mean_anomaly_score"].to_numpy()
    scored["suspicion_score"] = (
        np.searchsorted(legitimate, scores, side="right") / len(legitimate) * 100
    )

    return scored


def run_isolation_forest(
    df: pd.DataFrame,
    n_estimators: int = 100,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = prepare_features(df)

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    model = IsolationForest(
        n_estimators=n_estimators,
        contamination="auto",
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(scaled_features)

    scored = df.copy()
    scored["anomaly_score"] = -model.decision_function(scaled_features)
    scored["is_anomaly"] = model.predict(scaled_features) == -1

    return scored, aggregate_player_scores(scored)


def run_lof(
    df: pd.DataFrame,
    n_neighbors: int = 20,
    feature_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = prepare_features(df, feature_columns)

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    model = LocalOutlierFactor(
        n_neighbors=n_neighbors,
        contamination="auto",
        n_jobs=-1,
    )
    predictions = model.fit_predict(scaled_features)

    scored = df.copy()
    scored["anomaly_score"] = -model.negative_outlier_factor_
    scored["is_anomaly"] = predictions == -1

    return scored, aggregate_player_scores(scored)


def run_one_class_svm(
    df: pd.DataFrame,
    max_train_samples: int = 20000,
    nu: float = 0.05,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    features = prepare_features(df)

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    train_size = min(max_train_samples, len(df))
    rng = np.random.default_rng(random_state)
    train_indices = rng.choice(len(df), size=train_size, replace=False)

    model = OneClassSVM(kernel="rbf", gamma="scale", nu=nu)
    model.fit(scaled_features[train_indices])

    scored = df.copy()
    scored["anomaly_score"] = -model.decision_function(scaled_features)
    scored["is_anomaly"] = model.predict(scaled_features) == -1

    return scored, aggregate_player_scores(scored)