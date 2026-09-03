import math
from pathlib import Path

import pandas as pd

from ..parser.demo_parser import DemoParser

from ..features.aim import (
    angular_acceleration,
    angular_acceleration_magnitude,
    angular_speed,
    angular_velocity,
)


IGNORED_WEAPONS = {
    "weapon_flashbang",
    "weapon_smokegrenade",
    "weapon_decoy",
    "weapon_hegrenade",
    "weapon_incgrenade",
    "weapon_molotov",
}


def safe_int(value) -> int | None:
    if pd.isna(value):
        return None

    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return None


def safe_float(value) -> float | None:
    if pd.isna(value):
        return None

    try:
        value = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    return value if math.isfinite(value) else None


def safe_bool(value) -> bool | None:
    if pd.isna(value):
        return None

    return bool(value)


def is_valid_player(steamid, player_name) -> bool:
    steamid = safe_int(steamid)
    return steamid is not None and steamid > 0 and isinstance(player_name, str) and bool(player_name.strip())


def is_ignored_weapon(weapon) -> bool:
    if not isinstance(weapon, str) or not weapon.strip():
        return True

    weapon = weapon.strip().lower()
    return weapon in IGNORED_WEAPONS or "knife" in weapon


class DatasetBuilder:
    def __init__(self):
        self.samples: list[dict] = []

    def process_demo(
        self,
        demo_path: str | Path,
    ) -> None:
        demo_path = Path(demo_path)

        parser = DemoParser(demo_path)

        metadata = parser.get_match_metadata()

        self._add_shot_samples(
            parser,
            demo_path,
            metadata,
        )

        self._add_hit_samples(
            parser,
            demo_path,
            metadata,
        )

        self._add_kill_samples(
            parser,
            demo_path,
            metadata,
        )

    def _base_sample(
        self,
        demo_path: Path,
        metadata: dict,
        tick: int,
        event_type: str,
        steamid: int,
        player_name: str,
        weapon: str,
    ) -> dict:
        return {
            "match_id": demo_path.stem,
            "map_name": metadata["map_name"],
            "patch_version": metadata["patch_version"],
            "demo_version": metadata["demo_version"],
            "tick": tick,
            "event_type": event_type,
            "steamid": steamid,
            "player_name": player_name,
            "weapon": weapon,
        }

    def _add_shot_samples(self, parser: DemoParser, demo_path: Path, metadata: dict) -> None:
        shots = parser.get_shots()

        for shot in shots.itertuples(index=False):
            tick = safe_int(shot.tick)
            steamid = safe_int(shot.user_steamid)

            if tick is None or not is_valid_player(steamid, shot.user_name):
                continue

            if is_ignored_weapon(shot.weapon):
                continue

            sample = self._base_sample(
                demo_path=demo_path,
                metadata=metadata,
                tick=tick,
                event_type="shot",
                steamid=steamid,
                player_name=shot.user_name,
                weapon=shot.weapon.strip(),
            )

            self.samples.append(sample)

    def _add_hit_samples(self, parser: DemoParser, demo_path: Path, metadata: dict) -> None:
        hits = parser.get_hits()

        for hit in hits.itertuples(index=False):
            tick = safe_int(hit.tick)
            attacker_steamid = safe_int(hit.attacker_steamid)
            victim_steamid = safe_int(hit.user_steamid)

            if tick is None or not is_valid_player(attacker_steamid, hit.attacker_name):
                continue

            if victim_steamid is None or victim_steamid <= 0:
                continue

            if attacker_steamid == victim_steamid:
                continue

            if is_ignored_weapon(hit.weapon):
                continue

            sample = self._base_sample(
                demo_path=demo_path,
                metadata=metadata,
                tick=tick,
                event_type="hit",
                steamid=attacker_steamid,
                player_name=hit.attacker_name,
                weapon=hit.weapon.strip(),
            )

            sample.update(
                {
                    "victim_steamid": victim_steamid,
                    "victim_name": hit.user_name,
                    "damage_health": safe_int(hit.dmg_health),
                    "damage_armor": safe_int(hit.dmg_armor),
                    "victim_health": safe_int(hit.health),
                    "victim_armor": safe_int(hit.armor),
                    "hitgroup": hit.hitgroup if isinstance(hit.hitgroup, str) else None,
                }
            )

            self.samples.append(sample)

    def _add_kill_samples(self, parser: DemoParser, demo_path: Path, metadata: dict) -> None:
        kills = parser.get_kills()

        for kill in kills.itertuples(index=False):
            tick = safe_int(kill.tick)
            attacker_steamid = safe_int(kill.attacker_steamid)
            victim_steamid = safe_int(kill.user_steamid)

            if tick is None or not is_valid_player(attacker_steamid, kill.attacker_name):
                continue

            if victim_steamid is None or victim_steamid <= 0:
                continue

            if attacker_steamid == victim_steamid:
                continue

            if is_ignored_weapon(kill.weapon):
                continue

            sample = self._base_sample(
                demo_path=demo_path,
                metadata=metadata,
                tick=tick,
                event_type="kill",
                steamid=attacker_steamid,
                player_name=kill.attacker_name,
                weapon=kill.weapon.strip(),
            )

            sample.update(
                {
                    "victim_steamid": victim_steamid,
                    "victim_name": kill.user_name,
                    "headshot": safe_bool(kill.headshot),
                    "distance": safe_float(kill.distance),
                    "hitgroup": kill.hitgroup if isinstance(kill.hitgroup, str) else None,
                    "noscope": safe_bool(kill.noscope),
                    "penetrated": safe_int(kill.penetrated),
                    "thrusmoke": safe_bool(kill.thrusmoke),
                }
            )

            self.samples.append(sample)

    def process_directory(
        self,
        demo_directory: str | Path,
    ) -> None:
        demo_directory = Path(demo_directory)

        demo_files = sorted(
            demo_directory.glob("*.dem")
        )

        if not demo_files:
            raise FileNotFoundError(
                f"No .dem files found in "
                f"{demo_directory}"
            )

        for demo_path in demo_files:
            print(
                f"Processing: {demo_path.name}"
            )

            self.process_demo(demo_path)

    def build(self) -> pd.DataFrame:
        dataset = pd.DataFrame(self.samples)

        if dataset.empty:
            return dataset

        return dataset.sort_values(
            ["match_id", "tick", "event_type"]
        ).reset_index(drop=True)

    def build_player_samples(self) -> pd.DataFrame:
        dataset = self.build()

        if dataset.empty:
            return pd.DataFrame()

        player_rows = []

        grouped = dataset.groupby(
            ["match_id", "steamid"],
            dropna=False,
        )

        for (match_id, steamid), player_data in grouped:
            shots = player_data[
                player_data["event_type"] == "shot"
            ]

            hits = player_data[
                player_data["event_type"] == "hit"
            ]

            kills = player_data[
                player_data["event_type"] == "kill"
            ]

            shot_count = len(shots)
            hit_count = len(hits)
            kill_count = len(kills)

            if "headshot" in kills.columns:
                headshot_count = int(
                    kills["headshot"]
                    .fillna(False)
                    .astype(bool)
                    .sum()
                )
            else:
                headshot_count = 0

            if "damage_health" in hits.columns:
                total_damage = int(
                    hits["damage_health"]
                    .fillna(0)
                    .sum()
                )
            else:
                total_damage = 0

            accuracy = (
                hit_count / shot_count
                if shot_count > 0
                else 0.0
            )

            headshot_ratio = (
                headshot_count / kill_count
                if kill_count > 0
                else 0.0
            )

            mean_damage_per_hit = (
                total_damage / hit_count
                if hit_count > 0
                else 0.0
            )

            kills_per_shot = (
                kill_count / shot_count
                if shot_count > 0
                else 0.0
            )

            first_row = player_data.iloc[0]

            player_rows.append(
                {
                    "match_id": match_id,
                    "map_name": first_row["map_name"],
                    "steamid": int(steamid),
                    "player_name": first_row["player_name"],
                    "shots": shot_count,
                    "hits": hit_count,
                    "kills": kill_count,
                    "headshots": headshot_count,
                    "accuracy": accuracy,
                    "headshot_ratio": headshot_ratio,
                    "total_damage": total_damage,
                    "mean_damage_per_hit": mean_damage_per_hit,
                    "kills_per_shot": kills_per_shot,
                }
            )

        return pd.DataFrame(player_rows)

    def build_temporal_windows(
        self,
        demo_directory: str | Path,
        window_size: int = 32,
    ) -> pd.DataFrame:
        demo_directory = Path(demo_directory)

        rows = []

        demo_files = sorted(
            demo_directory.glob("*.dem")
        )

        for demo_path in demo_files:
            parser = DemoParser(demo_path)

            ticks = parser.get_player_ticks_df()
            shots = parser.get_shots()

            required_tick_columns = ["tick", "steamid", "X", "Y", "Z", "yaw", "pitch"]

            ticks = ticks.dropna(subset=required_tick_columns).copy()
            ticks = ticks.replace([float("inf"), float("-inf")], pd.NA)
            ticks = ticks.dropna(subset=required_tick_columns)

            if ticks.empty or shots.empty:
                continue

            for shot in shots.itertuples(index=False):
                shot_tick = safe_int(shot.tick)
                steamid = safe_int(shot.user_steamid)

                if shot_tick is None or not is_valid_player(steamid, shot.user_name):
                    continue

                if is_ignored_weapon(shot.weapon):
                    continue

                shot_tick = int(shot.tick)
                steamid = int(shot.user_steamid)

                player_ticks = ticks[
                    ticks["steamid"] == steamid
                ]

                window = player_ticks[
                    (player_ticks["tick"] <= shot_tick)
                    & (
                        player_ticks["tick"]
                        >= shot_tick - window_size + 1
                    )
                ].copy()

                window = (
                    window
                    .sort_values("tick")
                    .tail(window_size)
                )

                if len(window) < window_size:
                    continue

                window_id = (
                    f"{demo_path.stem}_"
                    f"{steamid}_"
                    f"{shot_tick}"
                )

                for offset, tick in enumerate(
                    window.itertuples(index=False)
                ):
                    rows.append(
                        {
                            "window_id": window_id,
                            "match_id": demo_path.stem,
                            "steamid": steamid,
                            "player_name":
                                shot.user_name,
                            "weapon": shot.weapon,
                            "shot_tick": shot_tick,
                            "window_offset": offset,
                            "tick": int(tick.tick),
                            "x": float(tick.X),
                            "y": float(tick.Y),
                            "z": float(tick.Z),
                            "yaw": float(tick.yaw),
                            "pitch": float(
                                tick.pitch
                            ),
                        }
                    )

        return pd.DataFrame(rows)

    def build_aim_features(
        self,
        temporal_windows: pd.DataFrame,
        tick_rate: float = 64.0,
    ) -> pd.DataFrame:
        if temporal_windows.empty:
            return pd.DataFrame()

        if tick_rate <= 0:
            raise ValueError(
                "tick_rate must be greater than zero"
            )

        feature_rows = []

        grouped = temporal_windows.groupby(
            "window_id",
            sort=False,
        )

        for window_id, window in grouped:
            window = (
                window
                .sort_values("window_offset")
                .reset_index(drop=True)
            )

            if len(window) < 3:
                continue

            yaw_velocities = []
            pitch_velocities = []
            angular_speeds = []
            velocity_ticks = []

            for index in range(1, len(window)):
                previous = window.iloc[index - 1]
                current = window.iloc[index]

                tick_delta = (
                    int(current["tick"])
                    - int(previous["tick"])
                )

                if tick_delta <= 0:
                    continue

                delta_time = tick_delta / tick_rate

                yaw_velocity, pitch_velocity = (
                    angular_velocity(
                        previous_yaw=float(
                            previous["yaw"]
                        ),
                        previous_pitch=float(
                            previous["pitch"]
                        ),
                        current_yaw=float(
                            current["yaw"]
                        ),
                        current_pitch=float(
                            current["pitch"]
                        ),
                        delta_time=delta_time,
                    )
                )

                yaw_velocities.append(yaw_velocity)
                pitch_velocities.append(
                    pitch_velocity
                )
                angular_speeds.append(
                    angular_speed(
                        yaw_velocity,
                        pitch_velocity,
                    )
                )
                velocity_ticks.append(
                    int(current["tick"])
                )

            if len(angular_speeds) < 2:
                continue

            acceleration_magnitudes = []

            for index in range(
                1,
                len(yaw_velocities),
            ):
                tick_delta = (
                    velocity_ticks[index]
                    - velocity_ticks[index - 1]
                )

                if tick_delta <= 0:
                    continue

                delta_time = tick_delta / tick_rate

                (
                    yaw_acceleration,
                    pitch_acceleration,
                ) = angular_acceleration(
                    previous_yaw_velocity=(
                        yaw_velocities[index - 1]
                    ),
                    previous_pitch_velocity=(
                        pitch_velocities[index - 1]
                    ),
                    current_yaw_velocity=(
                        yaw_velocities[index]
                    ),
                    current_pitch_velocity=(
                        pitch_velocities[index]
                    ),
                    delta_time=delta_time,
                )

                acceleration_magnitudes.append(
                    angular_acceleration_magnitude(
                        yaw_acceleration,
                        pitch_acceleration,
                    )
                )

            if not acceleration_magnitudes:
                continue

            first_row = window.iloc[0]

            speed_series = pd.Series(
                angular_speeds,
                dtype=float,
            )

            acceleration_series = pd.Series(
                acceleration_magnitudes,
                dtype=float,
            )

            feature_values = [
                speed_series.mean(),
                speed_series.max(),
                speed_series.std(ddof=0),
                acceleration_series.mean(),
                acceleration_series.max(),
                acceleration_series.std(ddof=0),
            ]

            if any(not math.isfinite(float(value)) for value in feature_values):
                continue

            feature_rows.append(
                {
                    "window_id": window_id,
                    "match_id": first_row["match_id"],
                    "steamid": int(first_row["steamid"]),
                    "player_name": first_row["player_name"],
                    "weapon": first_row["weapon"],
                    "shot_tick": int(first_row["shot_tick"]),
                    "mean_angular_speed": float(feature_values[0]),
                    "max_angular_speed": float(feature_values[1]),
                    "std_angular_speed": float(feature_values[2]),
                    "mean_angular_acceleration": float(feature_values[3]),
                    "max_angular_acceleration": float(feature_values[4]),
                    "std_angular_acceleration": float(feature_values[5]),
                }
            )

        return pd.DataFrame(feature_rows)