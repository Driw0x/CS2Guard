from collections import defaultdict
from pathlib import Path

from cs2guard_demo.features.aim import (
    angular_acceleration,
    angular_acceleration_magnitude,
    angular_difference,
    angular_speed,
    angular_velocity,
    crosshair_to_target_distance,
    find_target_acquisition,
    max_tracking_error,
    mean_tracking_error,
    tracking_error_std,
    tracking_time_on_target_ratio,
    count_aim_corrections,
    find_potential_overshoots,
    find_potential_aim_snaps,
    associate_shots_with_aim_sequences,
)
from cs2guard_demo.parser.demo_parser import DemoParser


ROOT_DIR = Path(__file__).resolve().parents[2]
DEMO_PATH = ROOT_DIR / "data" / "raw" / "demos" / "test.dem"

# Demo tick snapshots are tick-level.
# This rate is used only for the local preview and must not be
# treated as subtick timing information.
TICK_RATE = 64.0
SAMPLE_INTERVAL = 1 / TICK_RATE
PREVIEW_SAMPLES = 20


def main():
    parser = DemoParser(DEMO_PATH)
    match = parser.get_match()

    print(f"Map: {match.map_name}")
    print(f"Patch: {match.patch_version}")
    print(f"Players: {len(match.players)}")
    print(f"Rounds: {len(match.rounds)}")
    print(f"Events: {len(match.events)}")

    ticks = parser.get_player_ticks()
    shots = parser.get_shots()

    print_aim_features_preview(
        ticks=ticks,
        shots=shots,
    )


def print_aim_features_preview(ticks, shots):
    """
    Print a preview of aim features around a real weapon_fire event.

    The preview:
    - selects a player who fired at least once,
    - selects one real shot,
    - builds an aim window around that shot,
    - computes aim features,
    - associates the shot with the resulting aim sequence.

    Timing is approximated from tick differences using TICK_RATE.
    This is only for the local smoke test and is not subtick timing.
    """
    ticks_by_game_tick = defaultdict(list)

    for tick in ticks:
        ticks_by_game_tick[tick.tick].append(tick)

    sorted_game_ticks = sorted(ticks_by_game_tick)

    samples = []
    selected_player_id = None
    selected_target_id = None

    # ---------------------------------------------------------
    # Select a player with at least one real shot
    # ---------------------------------------------------------

    for game_tick in sorted_game_ticks:
        current_ticks = ticks_by_game_tick[game_tick]

        for candidate in current_ticks:
            candidate_shots = shots[
                shots["user_steamid"] == candidate.steamid
            ]

            if not candidate_shots.empty:
                selected_player_id = candidate.steamid
                break

        if selected_player_id is not None:
            break

    if selected_player_id is None:
        print("\nNo player with shots found.")
        return

    # ---------------------------------------------------------
    # Select one real shot
    # ---------------------------------------------------------

    player_shots = (
        shots[
            shots["user_steamid"] == selected_player_id
        ]
        .sort_values("tick")
        .reset_index(drop=True)
    )

    if player_shots.empty:
        print("\nSelected player has no shots.")
        return

    selected_shot = player_shots.iloc[0]

    selected_shot_tick = int(
        selected_shot["tick"]
    )

    print(
        f"\nSelected shot: "
        f"{selected_shot['user_name']} | "
        f"tick {selected_shot_tick} | "
        f"{selected_shot['weapon']}"
    )

    # ---------------------------------------------------------
    # Build an aim window around the selected shot
    # ---------------------------------------------------------

    PRE_SHOT_TICKS = 12
    POST_SHOT_TICKS = 4

    window_start_tick = (
        selected_shot_tick - PRE_SHOT_TICKS
    )

    window_end_tick = (
        selected_shot_tick + POST_SHOT_TICKS
    )

    for game_tick in sorted_game_ticks:
        if game_tick < window_start_tick:
            continue

        if game_tick > window_end_tick:
            break

        current_ticks = ticks_by_game_tick[game_tick]

        player_tick = next(
            (
                tick
                for tick in current_ticks
                if tick.steamid == selected_player_id
            ),
            None,
        )

        if player_tick is None:
            continue

        # Select an opponent once for the whole preview window.
        if selected_target_id is None:
            target_tick = next(
                (
                    tick
                    for tick in current_ticks
                    if tick.team != player_tick.team
                ),
                None,
            )

            if target_tick is None:
                continue

            selected_target_id = target_tick.steamid

        target_tick = next(
            (
                tick
                for tick in current_ticks
                if tick.steamid == selected_target_id
            ),
            None,
        )

        if target_tick is None:
            continue

        distance = crosshair_to_target_distance(
            player_position=(
                player_tick.x,
                player_tick.y,
                player_tick.z,
            ),
            view_yaw=player_tick.yaw,
            view_pitch=player_tick.pitch,
            target_position=(
                target_tick.x,
                target_tick.y,
                target_tick.z,
            ),
        )

        samples.append(
            (
                player_tick,
                target_tick,
                distance,
            )
        )

    if len(samples) < 2:
        print(
            "\nNot enough tick data "
            "around selected shot."
        )
        return

    # ---------------------------------------------------------
    # Aim motion features
    # ---------------------------------------------------------

    print("\n=== AIM FEATURES PREVIEW ===")

    distances = []
    timestamps = []
    speeds = []

    previous_velocity = None

    for index, (player, target, distance) in enumerate(samples):
        distances.append(distance)

        timestamp = (
            player.tick
            - samples[0][0].tick
        ) / TICK_RATE

        timestamps.append(timestamp)

        print(
            f"\nTick {player.tick} | "
            f"{player.player_name} -> "
            f"{target.player_name}"
        )

        print(
            f"Crosshair distance: "
            f"{distance:.2f}°"
        )

        if index == 0:
            speeds.append(0.0)
            continue

        previous_player = samples[index - 1][0]

        tick_delta = (
            player.tick
            - previous_player.tick
        )

        if tick_delta <= 0:
            speeds.append(0.0)
            continue

        delta_time = (
            tick_delta / TICK_RATE
        )

        yaw_velocity, pitch_velocity = angular_velocity(
            previous_yaw=previous_player.yaw,
            previous_pitch=previous_player.pitch,
            current_yaw=player.yaw,
            current_pitch=player.pitch,
            delta_time=delta_time,
        )

        speed = angular_speed(
            yaw_velocity,
            pitch_velocity,
        )

        speeds.append(speed)

        print(
            f"Angular speed: "
            f"{speed:.2f} °/s"
        )

        if previous_velocity is not None:
            yaw_acceleration, pitch_acceleration = (
                angular_acceleration(
                    previous_yaw_velocity=previous_velocity[0],
                    previous_pitch_velocity=previous_velocity[1],
                    current_yaw_velocity=yaw_velocity,
                    current_pitch_velocity=pitch_velocity,
                    delta_time=delta_time,
                )
            )

            acceleration = (
                angular_acceleration_magnitude(
                    yaw_acceleration,
                    pitch_acceleration,
                )
            )

            print(
                f"Angular acceleration: "
                f"{acceleration:.2f} °/s²"
            )

        previous_velocity = (
            yaw_velocity,
            pitch_velocity,
        )

    # ---------------------------------------------------------
    # Tracking summary
    # ---------------------------------------------------------

    print("\n=== TRACKING SUMMARY ===")

    print(
        f"Mean tracking error: "
        f"{mean_tracking_error(distances):.2f}°"
    )

    print(
        f"Max tracking error: "
        f"{max_tracking_error(distances):.2f}°"
    )

    print(
        f"Tracking error std: "
        f"{tracking_error_std(distances):.2f}°"
    )

    print(
        f"Time on target: "
        f"{tracking_time_on_target_ratio(distances) * 100:.1f}%"
    )

    # ---------------------------------------------------------
    # Target acquisition
    # ---------------------------------------------------------

    acquisition_index = find_target_acquisition(
        distances
    )

    if acquisition_index is None:
        print(
            "Target acquisition: "
            "not detected"
        )
    else:
        acquisition_tick = (
            samples[acquisition_index][0].tick
        )

        print(
            f"Target acquisition: "
            f"tick {acquisition_tick}"
        )

    # ---------------------------------------------------------
    # Aim corrections
    # ---------------------------------------------------------

    corrections = count_aim_corrections(
        distances
    )

    print(
        f"Aim corrections: "
        f"{corrections}"
    )

    # ---------------------------------------------------------
    # Potential overshoots
    # ---------------------------------------------------------

    overshoot_indices = find_potential_overshoots(
        distances
    )

    if not overshoot_indices:
        print(
            "Potential overshoots: "
            "none detected"
        )
    else:
        overshoot_ticks = [
            samples[index][0].tick
            for index in overshoot_indices
        ]

        print(
            f"Potential overshoots: "
            f"{len(overshoot_ticks)}"
        )

        print(
            f"Overshoot ticks: "
            f"{overshoot_ticks}"
        )

    # ---------------------------------------------------------
    # Potential aim snaps
    # ---------------------------------------------------------

    snap_windows = find_potential_aim_snaps(
        angular_distances=distances,
        angular_speeds=speeds,
        timestamps=timestamps,
    )

    if not snap_windows:
        print(
            "Potential aim snaps: "
            "none detected"
        )
    else:
        print(
            f"Potential aim snaps: "
            f"{len(snap_windows)}"
        )

        for start_index, end_index in snap_windows:
            start_tick = (
                samples[start_index][0].tick
            )

            end_tick = (
                samples[end_index][0].tick
            )

            print(
                f"  Snap candidate: "
                f"tick {start_tick} -> {end_tick}"
            )

    # ---------------------------------------------------------
    # Associate the real shot with the aim window
    # ---------------------------------------------------------

    sample_ticks = [
        sample[0].tick
        for sample in samples
    ]

    sequence_windows = [
        (0, len(samples) - 1)
    ]

    sequences = associate_shots_with_aim_sequences(
        sequence_windows=sequence_windows,
        sample_ticks=sample_ticks,
        shot_ticks=[selected_shot_tick],
    )

    print("\n=== SHOT ASSOCIATION ===")

    for sequence in sequences:
        start_tick = (
            sample_ticks[sequence.start_index]
        )

        end_tick = (
            sample_ticks[sequence.end_index]
        )

        if sequence.shot_tick is None:
            print(
                f"Aim sequence "
                f"{start_tick} -> {end_tick}: "
                f"no associated shot"
            )
        else:
            print(
                f"Aim sequence "
                f"{start_tick} -> {end_tick}: "
                f"shot at tick {sequence.shot_tick}"
            )


if __name__ == "__main__":
    main()