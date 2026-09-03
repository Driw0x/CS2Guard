from collections import defaultdict
from pathlib import Path
from cs2guard_demo.features.aim import angular_acceleration, angular_acceleration_magnitude, angular_speed, angular_velocity, associate_shots_with_aim_sequences, count_aim_corrections, crosshair_to_target_distance, find_potential_aim_snaps, find_potential_overshoots, find_target_acquisition, max_tracking_error, mean_tracking_error, tracking_error_std, tracking_time_on_target_ratio
from cs2guard_demo.parser.demo_parser import DemoParser
from cs2guard_demo.visualization.aim import plot_aim_trajectory


ROOT_DIR = Path(__file__).resolve().parents[2]
DEMO_PATH = Path('data/raw/train_sources/demo/test.dem')
TICK_RATE = 64.0
PRE_SHOT_TICKS = 12
POST_SHOT_TICKS = 4
EXCLUDED_AIM_WEAPONS = {'weapon_molotov', 'weapon_incgrenade', 'weapon_hegrenade', 'weapon_flashbang', 'weapon_smokegrenade', 'weapon_decoy', 'weapon_knife', 'weapon_taser'}


def main():
    parser = DemoParser(DEMO_PATH)
    ticks = parser.get_player_ticks()
    shots = parser.get_shots()
    hits = parser.get_hits()
    print_aim_features_preview(ticks=ticks, shots=shots, hits=hits)


def print_aim_features_preview(ticks, shots, hits):
    ticks_by_game_tick = defaultdict(list)

    for tick in ticks:
        ticks_by_game_tick[tick.tick].append(tick)

    sorted_game_ticks = sorted(ticks_by_game_tick)
    valid_hits = hits[~hits['weapon'].isin(EXCLUDED_AIM_WEAPONS)].sort_values('tick').reset_index(drop=True)

    if valid_hits.empty:
        print('\nNo firearm hit available for aim validation.')
        return

    selected_hit = valid_hits.iloc[0]
    selected_hit_tick = int(selected_hit['tick'])
    selected_player_id = int(selected_hit['attacker_steamid'])
    selected_target_id = int(selected_hit['user_steamid'])
    selected_weapon = selected_hit['weapon']
    player_shots = shots[shots['user_steamid'] == selected_player_id].copy()
    player_shots = player_shots[player_shots['tick'] <= selected_hit_tick]

    if player_shots.empty:
        print('\nNo weapon_fire found before the selected hit.')
        return

    player_shots['tick_distance'] = selected_hit_tick - player_shots['tick']
    matching_shots = player_shots[player_shots['tick_distance'] <= 2]

    if matching_shots.empty:
        print('\nNo matching weapon_fire found for selected hit.')
        return

    selected_shot = matching_shots.sort_values('tick_distance').iloc[0]
    selected_shot_tick = int(selected_shot['tick'])
    print('\n=== SELECTED AIM SEQUENCE ===')
    print(f"Player: {selected_hit['attacker_name']}")
    print(f"Target: {selected_hit['user_name']}")
    print(f'Weapon: {selected_weapon}')
    print(f'Shot tick: {selected_shot_tick}')
    print(f'Hit tick: {selected_hit_tick}')
    window_start_tick = selected_shot_tick - PRE_SHOT_TICKS
    window_end_tick = selected_shot_tick + POST_SHOT_TICKS
    samples = []

    for game_tick in sorted_game_ticks:
        if game_tick < window_start_tick:
            continue

        if game_tick > window_end_tick:
            break

        current_ticks = ticks_by_game_tick[game_tick]
        player_tick = next((tick for tick in current_ticks if tick.steamid == selected_player_id), None)
        target_tick = next((tick for tick in current_ticks if tick.steamid == selected_target_id), None)

        if player_tick is None or target_tick is None:
            continue

        distance = crosshair_to_target_distance(player_position=(player_tick.x, player_tick.y, player_tick.z), view_yaw=player_tick.yaw, view_pitch=player_tick.pitch, target_position=(target_tick.x, target_tick.y, target_tick.z))
        samples.append((player_tick, target_tick, distance))

    if len(samples) < 2:
        print('\nNot enough tick data around selected shot.')
        return

    print('\n=== AIM FEATURES PREVIEW ===')
    distances = []
    timestamps = []
    speeds = []
    previous_velocity = None

    for index, (player, target, distance) in enumerate(samples):
        distances.append(distance)
        timestamp = (player.tick - samples[0][0].tick) / TICK_RATE
        timestamps.append(timestamp)
        print(f'\nTick {player.tick} | {player.player_name} -> {target.player_name}')
        print(f'Crosshair distance: {distance:.2f}°')

        if index == 0:
            speeds.append(0.0)
            continue

        previous_player = samples[index - 1][0]
        tick_delta = player.tick - previous_player.tick

        if tick_delta <= 0:
            speeds.append(0.0)
            continue

        delta_time = tick_delta / TICK_RATE
        yaw_velocity, pitch_velocity = angular_velocity(previous_yaw=previous_player.yaw, previous_pitch=previous_player.pitch, current_yaw=player.yaw, current_pitch=player.pitch, delta_time=delta_time)
        speed = angular_speed(yaw_velocity, pitch_velocity)
        speeds.append(speed)
        print(f'Angular speed: {speed:.2f} °/s')

        if previous_velocity is not None:
            yaw_acceleration, pitch_acceleration = angular_acceleration(previous_yaw_velocity=previous_velocity[0], previous_pitch_velocity=previous_velocity[1], current_yaw_velocity=yaw_velocity, current_pitch_velocity=pitch_velocity, delta_time=delta_time)
            acceleration = angular_acceleration_magnitude(yaw_acceleration, pitch_acceleration)
            print(f'Angular acceleration: {acceleration:.2f} °/s²')

        previous_velocity = (yaw_velocity, pitch_velocity)

    print('\n=== TRACKING SUMMARY ===')
    print(f'Mean tracking error: {mean_tracking_error(distances):.2f}°')
    print(f'Max tracking error: {max_tracking_error(distances):.2f}°')
    print(f'Tracking error std: {tracking_error_std(distances):.2f}°')
    print(f'Time on target: {tracking_time_on_target_ratio(distances) * 100:.1f}%')
    acquisition_index = find_target_acquisition(distances)

    if acquisition_index is None:
        print('Target acquisition: not detected')
    else:
        acquisition_tick = samples[acquisition_index][0].tick
        print(f'Target acquisition: tick {acquisition_tick}')

    corrections = count_aim_corrections(distances)
    print(f'Aim corrections: {corrections}')
    overshoot_indices = find_potential_overshoots(distances)
    overshoot_ticks = [samples[index][0].tick for index in overshoot_indices]

    if not overshoot_ticks:
        print('Potential overshoots: none detected')
    else:
        print(f'Potential overshoots: {len(overshoot_ticks)}')
        print(f'Overshoot ticks: {overshoot_ticks}')

    snap_windows = find_potential_aim_snaps(angular_distances=distances, angular_speeds=speeds, timestamps=timestamps)

    if not snap_windows:
        print('Potential aim snaps: none detected')
    else:
        print(f'Potential aim snaps: {len(snap_windows)}')

        for start_index, end_index in snap_windows:
            start_tick = samples[start_index][0].tick
            end_tick = samples[end_index][0].tick
            print(f'  Snap candidate: tick {start_tick} -> {end_tick}')

    sample_ticks = [sample[0].tick for sample in samples]
    sequence_windows = [(0, len(samples) - 1)]
    sequences = associate_shots_with_aim_sequences(sequence_windows=sequence_windows, sample_ticks=sample_ticks, shot_ticks=[selected_shot_tick])
    print('\n=== SHOT ASSOCIATION ===')

    for sequence in sequences:
        start_tick = sample_ticks[sequence.start_index]
        end_tick = sample_ticks[sequence.end_index]

        if sequence.shot_tick is None:
            print(f'Aim sequence {start_tick} -> {end_tick}: no associated shot')
        else:
            print(f'Aim sequence {start_tick} -> {end_tick}: shot at tick {sequence.shot_tick}')

    snap_tick_windows = [(sample_ticks[start_index], sample_ticks[end_index]) for start_index, end_index in snap_windows]
    plot_aim_trajectory(sample_ticks=sample_ticks, angular_distances=distances, shot_ticks=[selected_shot_tick], hit_ticks=[selected_hit_tick], overshoot_ticks=overshoot_ticks, snap_windows=snap_tick_windows, title=f"{selected_hit['attacker_name']} -> {selected_hit['user_name']} | {selected_weapon}")

if __name__ == '__main__':
    main()
