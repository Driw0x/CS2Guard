import math
import pytest
from cs2guard_demo.features.aim import normalize_angle, direction_to_angles, angular_difference, crosshair_target_error, angular_distance, crosshair_to_target_distance, angular_velocity, angular_speed, angular_acceleration, angular_acceleration_magnitude, find_target_acquisition, find_aim_response, reaction_time, mean_tracking_error, max_tracking_error, tracking_error_std, tracking_time_on_target_ratio, count_aim_corrections, find_potential_overshoots, find_potential_aim_snaps, associate_shots_with_aim_sequences


def test_normalize_angle():
    assert normalize_angle(0.0) == 0.0
    assert normalize_angle(180.0) == -180.0
    assert normalize_angle(360.0) == 0.0
    assert normalize_angle(-360.0) == 0.0
    assert normalize_angle(540.0) == -180.0


def test_direction_to_angles_forward():
    source = (0.0, 0.0, 0.0)
    target = (100.0, 0.0, 0.0)
    yaw, pitch = direction_to_angles(source, target)
    assert math.isclose(yaw, 0.0, abs_tol=1e-06)
    assert math.isclose(pitch, 0.0, abs_tol=1e-06)


def test_direction_to_angles_right():
    source = (0.0, 0.0, 0.0)
    target = (0.0, 100.0, 0.0)
    yaw, pitch = direction_to_angles(source, target)
    assert math.isclose(yaw, 90.0, abs_tol=1e-06)
    assert math.isclose(pitch, 0.0, abs_tol=1e-06)


def test_direction_to_angles_up():
    source = (0.0, 0.0, 0.0)
    target = (100.0, 0.0, 100.0)
    yaw, pitch = direction_to_angles(source, target)
    assert math.isclose(yaw, 0.0, abs_tol=1e-06)
    assert math.isclose(pitch, -45.0, abs_tol=1e-06)


def test_angular_difference_basic():
    assert math.isclose(angular_difference(10.0, 20.0), 10.0, abs_tol=1e-06)
    assert math.isclose(angular_difference(20.0, 10.0), -10.0, abs_tol=1e-06)


def test_angular_difference_wraparound():
    assert math.isclose(angular_difference(179.0, -179.0), 2.0, abs_tol=1e-06)
    assert math.isclose(angular_difference(-179.0, 179.0), -2.0, abs_tol=1e-06)


def test_crosshair_target_error():
    yaw_error, pitch_error = crosshair_target_error(view_yaw=10.0, view_pitch=5.0, target_yaw=15.0, target_pitch=2.0)
    assert math.isclose(yaw_error, 5.0, abs_tol=1e-06)
    assert math.isclose(pitch_error, -3.0, abs_tol=1e-06)


def test_angular_distance():
    distance = angular_distance(view_yaw=0.0, view_pitch=0.0, target_yaw=3.0, target_pitch=4.0)
    assert math.isclose(distance, 5.0, abs_tol=1e-06)


def test_crosshair_to_target_distance_perfect_alignment():
    distance = crosshair_to_target_distance(player_position=(0.0, 0.0, 0.0), view_yaw=0.0, view_pitch=0.0, target_position=(100.0, 0.0, 0.0))
    assert math.isclose(distance, 0.0, abs_tol=1e-06)


def test_crosshair_to_target_distance_90_degrees():
    distance = crosshair_to_target_distance(player_position=(0.0, 0.0, 0.0), view_yaw=0.0, view_pitch=0.0, target_position=(0.0, 100.0, 0.0))
    assert math.isclose(distance, 90.0, abs_tol=1e-06)


def test_angular_velocity():
    yaw_velocity, pitch_velocity = angular_velocity(previous_yaw=10.0, previous_pitch=5.0, current_yaw=20.0, current_pitch=1.0, delta_time=0.5)
    assert math.isclose(yaw_velocity, 20.0, abs_tol=1e-06)
    assert math.isclose(pitch_velocity, -8.0, abs_tol=1e-06)


def test_angular_velocity_wraparound():
    yaw_velocity, pitch_velocity = angular_velocity(previous_yaw=179.0, previous_pitch=0.0, current_yaw=-179.0, current_pitch=0.0, delta_time=0.1)
    assert math.isclose(yaw_velocity, 20.0, abs_tol=1e-06)
    assert math.isclose(pitch_velocity, 0.0, abs_tol=1e-06)


def test_angular_velocity_negative():
    yaw_velocity, pitch_velocity = angular_velocity(previous_yaw=20.0, previous_pitch=10.0, current_yaw=10.0, current_pitch=5.0, delta_time=0.5)
    assert math.isclose(yaw_velocity, -20.0, abs_tol=1e-06)
    assert math.isclose(pitch_velocity, -10.0, abs_tol=1e-06)


def test_angular_velocity_invalid_delta_time():
    with pytest.raises(ValueError):
        angular_velocity(previous_yaw=0.0, previous_pitch=0.0, current_yaw=10.0, current_pitch=10.0, delta_time=0.0)

    with pytest.raises(ValueError):
        angular_velocity(previous_yaw=0.0, previous_pitch=0.0, current_yaw=10.0, current_pitch=10.0, delta_time=-0.1)


def test_angular_speed():
    speed = angular_speed(yaw_velocity=300.0, pitch_velocity=400.0)
    assert math.isclose(speed, 500.0, abs_tol=1e-06)


def test_angular_acceleration():
    yaw_acceleration, pitch_acceleration = angular_acceleration(previous_yaw_velocity=100.0, previous_pitch_velocity=50.0, current_yaw_velocity=150.0, current_pitch_velocity=30.0, delta_time=0.5)
    assert math.isclose(yaw_acceleration, 100.0, abs_tol=1e-06)
    assert math.isclose(pitch_acceleration, -40.0, abs_tol=1e-06)


def test_angular_acceleration_negative():
    yaw_acceleration, pitch_acceleration = angular_acceleration(previous_yaw_velocity=200.0, previous_pitch_velocity=100.0, current_yaw_velocity=100.0, current_pitch_velocity=50.0, delta_time=0.5)
    assert math.isclose(yaw_acceleration, -200.0, abs_tol=1e-06)
    assert math.isclose(pitch_acceleration, -100.0, abs_tol=1e-06)


def test_angular_acceleration_invalid_delta_time():
    with pytest.raises(ValueError):
        angular_acceleration(previous_yaw_velocity=0.0, previous_pitch_velocity=0.0, current_yaw_velocity=100.0, current_pitch_velocity=100.0, delta_time=0.0)

    with pytest.raises(ValueError):
        angular_acceleration(previous_yaw_velocity=0.0, previous_pitch_velocity=0.0, current_yaw_velocity=100.0, current_pitch_velocity=100.0, delta_time=-0.1)


def test_angular_acceleration_magnitude():
    magnitude = angular_acceleration_magnitude(yaw_acceleration=300.0, pitch_acceleration=400.0)
    assert math.isclose(magnitude, 500.0, abs_tol=1e-06)


def test_find_target_acquisition():
    distances = [14.2, 10.8, 6.1, 2.7, 1.4, 0.8]
    acquisition = find_target_acquisition(distances)
    assert acquisition == 3


def test_target_acquisition_requires_stability():
    distances = [10.0, 2.5, 5.0, 2.0, 1.0]
    acquisition = find_target_acquisition(distances, threshold=3.0, min_consecutive_samples=2)
    assert acquisition == 3


def test_target_acquisition_not_found():
    distances = [15.0, 10.0, 8.0, 5.0]
    acquisition = find_target_acquisition(distances)
    assert acquisition is None


def test_target_acquisition_empty_sequence():
    assert find_target_acquisition([]) is None


def test_target_acquisition_first_samples():
    distances = [1.0, 2.0, 10.0]
    acquisition = find_target_acquisition(distances, threshold=3.0, min_consecutive_samples=2)
    assert acquisition == 0


def test_target_acquisition_invalid_threshold():
    with pytest.raises(ValueError):
        find_target_acquisition([1.0, 2.0], threshold=-1.0)


def test_target_acquisition_invalid_min_samples():
    with pytest.raises(ValueError):
        find_target_acquisition([1.0, 2.0], min_consecutive_samples=0)


def test_find_aim_response():
    distances = [15.0, 15.1, 15.0, 14.2, 13.0, 10.0]
    response = find_aim_response(angular_distances=distances, start_index=0, min_improvement=0.5, min_consecutive_samples=2)
    assert response == 3


def test_find_aim_response_not_found():
    distances = [15.0, 15.1, 15.0, 15.2, 15.1]
    response = find_aim_response(angular_distances=distances, start_index=0)
    assert response is None


def test_find_aim_response_after_start_index():
    distances = [20.0, 18.0, 17.0, 16.0, 16.2, 15.5, 14.5]
    response = find_aim_response(angular_distances=distances, start_index=4, min_improvement=0.5, min_consecutive_samples=2)
    assert response == 5


def test_find_aim_response_start_index_out_of_range():
    response = find_aim_response(angular_distances=[10.0, 9.0], start_index=5)
    assert response is None


def test_find_aim_response_invalid_start_index():
    with pytest.raises(ValueError):
        find_aim_response(angular_distances=[10.0, 9.0], start_index=-1)


def test_find_aim_response_invalid_min_improvement():
    with pytest.raises(ValueError):
        find_aim_response(angular_distances=[10.0, 9.0], start_index=0, min_improvement=-0.1)


def test_find_aim_response_invalid_min_samples():
    with pytest.raises(ValueError):
        find_aim_response(angular_distances=[10.0, 9.0], start_index=0, min_consecutive_samples=0)


def test_reaction_time():
    value = reaction_time(stimulus_index=100, response_index=106, sample_interval=1 / 64)
    assert math.isclose(value, 0.09375, abs_tol=1e-06)


def test_reaction_time_zero():
    value = reaction_time(stimulus_index=100, response_index=100, sample_interval=1 / 64)
    assert math.isclose(value, 0.0, abs_tol=1e-06)


def test_reaction_time_response_before_stimulus():
    with pytest.raises(ValueError):
        reaction_time(stimulus_index=10, response_index=5, sample_interval=1 / 64)


def test_reaction_time_negative_index():
    with pytest.raises(ValueError):
        reaction_time(stimulus_index=-1, response_index=5, sample_interval=1 / 64)


def test_reaction_time_invalid_sample_interval():
    with pytest.raises(ValueError):
        reaction_time(stimulus_index=0, response_index=5, sample_interval=0.0)

    with pytest.raises(ValueError):
        reaction_time(stimulus_index=0, response_index=5, sample_interval=-0.1)


def test_mean_tracking_error():
    distances = [1.0, 2.0, 3.0, 4.0]
    result = mean_tracking_error(distances)
    assert math.isclose(result, 2.5, abs_tol=1e-06)


def test_mean_tracking_error_empty():
    with pytest.raises(ValueError):
        mean_tracking_error([])


def test_max_tracking_error():
    distances = [1.0, 4.5, 2.0, 3.0]
    result = max_tracking_error(distances)
    assert math.isclose(result, 4.5, abs_tol=1e-06)


def test_max_tracking_error_empty():
    with pytest.raises(ValueError):
        max_tracking_error([])


def test_tracking_error_std():
    distances = [1.0, 2.0, 3.0]
    result = tracking_error_std(distances)
    expected = math.sqrt(2 / 3)
    assert math.isclose(result, expected, abs_tol=1e-06)


def test_tracking_error_std_constant_values():
    distances = [2.0, 2.0, 2.0]
    result = tracking_error_std(distances)
    assert math.isclose(result, 0.0, abs_tol=1e-06)


def test_tracking_error_std_empty():
    with pytest.raises(ValueError):
        tracking_error_std([])


def test_tracking_time_on_target_ratio():
    distances = [2.0, 1.5, 4.0, 2.5]
    result = tracking_time_on_target_ratio(distances, threshold=3.0)
    assert math.isclose(result, 0.75, abs_tol=1e-06)


def test_tracking_time_on_target_ratio_all_on_target():
    distances = [1.0, 2.0, 3.0]
    result = tracking_time_on_target_ratio(distances, threshold=3.0)
    assert math.isclose(result, 1.0, abs_tol=1e-06)


def test_tracking_time_on_target_ratio_none_on_target():
    distances = [4.0, 5.0, 6.0]
    result = tracking_time_on_target_ratio(distances, threshold=3.0)
    assert math.isclose(result, 0.0, abs_tol=1e-06)


def test_tracking_time_on_target_ratio_includes_threshold():
    distances = [3.0, 4.0]
    result = tracking_time_on_target_ratio(distances, threshold=3.0)
    assert math.isclose(result, 0.5, abs_tol=1e-06)


def test_tracking_time_on_target_ratio_empty():
    with pytest.raises(ValueError):
        tracking_time_on_target_ratio([])


def test_tracking_time_on_target_ratio_invalid_threshold():
    with pytest.raises(ValueError):
        tracking_time_on_target_ratio([1.0, 2.0], threshold=-1.0)


def test_count_aim_corrections_no_correction():
    distances = [10.0, 8.0, 6.0, 4.0, 2.0]
    assert count_aim_corrections(distances) == 0


def test_count_aim_corrections_single_correction():
    distances = [10.0, 8.0, 6.0, 7.0, 8.0]
    assert count_aim_corrections(distances) == 1


def test_count_aim_corrections_multiple_corrections():
    distances = [10.0, 7.0, 4.0, 5.0, 3.0]
    assert count_aim_corrections(distances) == 2


def test_count_aim_corrections_ignores_small_changes():
    distances = [10.0, 8.0, 8.05, 7.0]
    assert count_aim_corrections(distances, min_change=0.1) == 0


def test_count_aim_corrections_empty():
    assert count_aim_corrections([]) == 0


def test_count_aim_corrections_not_enough_samples():
    assert count_aim_corrections([10.0, 5.0]) == 0


def test_count_aim_corrections_invalid_min_change():
    with pytest.raises(ValueError):
        count_aim_corrections([10.0, 5.0, 2.0], min_change=-0.1)


def test_find_potential_overshoots_detects_overshoot():
    distances = [10.0, 6.0, 3.0, 7.0, 9.0]
    assert find_potential_overshoots(distances) == [2]


def test_find_potential_overshoots_realistic_sequence():
    distances = [17.53, 10.5, 4.44, 3.92, 8.53, 13.75]
    assert find_potential_overshoots(distances) == [3]


def test_find_potential_overshoots_not_close_enough():
    distances = [15.0, 10.0, 6.0, 10.0]
    assert find_potential_overshoots(distances, proximity_threshold=5.0) == []


def test_find_potential_overshoots_departure_too_small():
    distances = [10.0, 4.0, 3.0, 3.5, 5.0]
    assert find_potential_overshoots(distances, min_departure=1.0) == []


def test_find_potential_overshoots_multiple():
    distances = [10.0, 3.0, 7.0, 2.0, 6.0]
    assert find_potential_overshoots(distances) == [1, 3]


def test_find_potential_overshoots_empty():
    assert find_potential_overshoots([]) == []


def test_find_potential_overshoots_invalid_proximity_threshold():
    with pytest.raises(ValueError):
        find_potential_overshoots([10.0, 2.0, 5.0], proximity_threshold=-1.0)


def test_find_potential_overshoots_invalid_min_departure():
    with pytest.raises(ValueError):
        find_potential_overshoots([10.0, 2.0, 5.0], min_departure=-1.0)


def test_find_potential_aim_snaps_detects_snap():
    distances = [20.0, 14.0, 8.0, 3.0]
    speeds = [0.0, 250.0, 400.0, 300.0]
    timestamps = [0.0, 0.03, 0.06, 0.09]
    assert find_potential_aim_snaps(distances, speeds, timestamps) == [(0, 3)]


def test_find_potential_aim_snaps_no_target_approach():
    distances = [20.0, 18.0, 15.0, 12.0]
    speeds = [0.0, 300.0, 400.0, 350.0]
    timestamps = [0.0, 0.03, 0.06, 0.09]
    assert find_potential_aim_snaps(distances, speeds, timestamps) == []


def test_find_potential_aim_snaps_speed_too_low():
    distances = [20.0, 12.0, 7.0, 3.0]
    speeds = [0.0, 80.0, 120.0, 100.0]
    timestamps = [0.0, 0.03, 0.06, 0.09]
    assert find_potential_aim_snaps(distances, speeds, timestamps, min_angular_speed=200.0) == []


def test_find_potential_aim_snaps_duration_too_long():
    distances = [20.0, 14.0, 8.0, 3.0]
    speeds = [0.0, 250.0, 400.0, 300.0]
    timestamps = [0.0, 0.1, 0.2, 0.3]
    assert find_potential_aim_snaps(distances, speeds, timestamps, max_duration=0.15) == []


def test_find_potential_aim_snaps_ignores_small_correction():
    distances = [4.0, 3.0, 2.0]
    speeds = [0.0, 300.0, 350.0]
    timestamps = [0.0, 0.03, 0.06]
    assert find_potential_aim_snaps(distances, speeds, timestamps, start_distance_threshold=10.0) == []


def test_find_potential_aim_snaps_detects_multiple():
    distances = [20.0, 12.0, 3.0, 15.0, 11.0, 2.0]
    speeds = [0.0, 350.0, 300.0, 0.0, 400.0, 350.0]
    timestamps = [0.0, 0.03, 0.06, 0.3, 0.33, 0.36]
    assert find_potential_aim_snaps(distances, speeds, timestamps) == [(0, 2), (3, 5)]


def test_find_potential_aim_snaps_empty():
    assert find_potential_aim_snaps([], [], []) == []


def test_find_potential_aim_snaps_mismatched_lengths():
    with pytest.raises(ValueError):
        find_potential_aim_snaps([20.0, 3.0], [300.0], [0.0, 0.05])


def test_find_potential_aim_snaps_invalid_start_threshold():
    with pytest.raises(ValueError):
        find_potential_aim_snaps([20.0, 3.0], [300.0, 300.0], [0.0, 0.05], start_distance_threshold=-1.0)


def test_find_potential_aim_snaps_invalid_target_threshold():
    with pytest.raises(ValueError):
        find_potential_aim_snaps([20.0, 3.0], [300.0, 300.0], [0.0, 0.05], target_distance_threshold=-1.0)


def test_find_potential_aim_snaps_invalid_speed():
    with pytest.raises(ValueError):
        find_potential_aim_snaps([20.0, 3.0], [300.0, 300.0], [0.0, 0.05], min_angular_speed=-1.0)


def test_find_potential_aim_snaps_invalid_duration():
    with pytest.raises(ValueError):
        find_potential_aim_snaps([20.0, 3.0], [300.0, 300.0], [0.0, 0.05], max_duration=0.0)


def test_find_potential_aim_snaps_rejects_unordered_timestamps():
    with pytest.raises(ValueError):
        find_potential_aim_snaps([20.0, 12.0, 3.0], [0.0, 300.0, 350.0], [0.0, 0.06, 0.03])


def test_find_potential_aim_snaps_does_not_duplicate_while_on_target():
    distances = [20.0, 12.0, 4.0, 3.0, 2.0]
    speeds = [0.0, 300.0, 400.0, 250.0, 100.0]
    timestamps = [0.0, 0.03, 0.06, 0.09, 0.12]
    assert find_potential_aim_snaps(distances, speeds, timestamps) == [(0, 2)]


def test_associate_shot_inside_sequence():
    sequences = associate_shots_with_aim_sequences(sequence_windows=[(1, 3)], sample_ticks=[100, 101, 102, 103, 104], shot_ticks=[102])
    assert len(sequences) == 1
    assert sequences[0].start_index == 1
    assert sequences[0].end_index == 3
    assert sequences[0].shot_tick == 102


def test_associate_shot_shortly_after_sequence():
    sequences = associate_shots_with_aim_sequences(sequence_windows=[(1, 3)], sample_ticks=[100, 101, 102, 103, 104], shot_ticks=[105], max_tick_distance=2)
    assert sequences[0].shot_tick == 105


def test_does_not_associate_distant_shot():
    sequences = associate_shots_with_aim_sequences(sequence_windows=[(1, 3)], sample_ticks=[100, 101, 102, 103, 104], shot_ticks=[110], max_tick_distance=2)
    assert sequences[0].shot_tick is None


def test_associate_first_matching_shot():
    sequences = associate_shots_with_aim_sequences(sequence_windows=[(0, 2)], sample_ticks=[100, 101, 102], shot_ticks=[101, 102])
    assert sequences[0].shot_tick == 101


def test_associate_multiple_sequences():
    sequences = associate_shots_with_aim_sequences(sequence_windows=[(0, 2), (3, 5)], sample_ticks=[100, 101, 102, 200, 201, 202], shot_ticks=[102, 203], max_tick_distance=1)
    assert sequences[0].shot_tick == 102
    assert sequences[1].shot_tick == 203


def test_associate_no_shots():
    sequences = associate_shots_with_aim_sequences(sequence_windows=[(0, 2)], sample_ticks=[100, 101, 102], shot_ticks=[])
    assert sequences[0].shot_tick is None


def test_associate_no_sequences():
    assert associate_shots_with_aim_sequences(sequence_windows=[], sample_ticks=[100, 101], shot_ticks=[101]) == []


def test_associate_invalid_negative_index():
    with pytest.raises(ValueError):
        associate_shots_with_aim_sequences(sequence_windows=[(-1, 2)], sample_ticks=[100, 101, 102], shot_ticks=[])


def test_associate_invalid_end_index():
    with pytest.raises(ValueError):
        associate_shots_with_aim_sequences(sequence_windows=[(0, 5)], sample_ticks=[100, 101, 102], shot_ticks=[])


def test_associate_start_after_end():
    with pytest.raises(ValueError):
        associate_shots_with_aim_sequences(sequence_windows=[(2, 1)], sample_ticks=[100, 101, 102], shot_ticks=[])


def test_associate_invalid_max_tick_distance():
    with pytest.raises(ValueError):
        associate_shots_with_aim_sequences(sequence_windows=[(0, 1)], sample_ticks=[100, 101], shot_ticks=[], max_tick_distance=-1)
