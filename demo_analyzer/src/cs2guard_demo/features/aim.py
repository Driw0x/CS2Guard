import math
from ..models.aim_sequence import AimSequence


def normalize_angle(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


def direction_to_angles(source: tuple[float, float, float], target: tuple[float, float, float]) -> tuple[float, float]:
    dx = target[0] - source[0]
    dy = target[1] - source[1]
    dz = target[2] - source[2]
    horizontal_distance = math.hypot(dx, dy)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = -math.degrees(math.atan2(dz, horizontal_distance))
    return (normalize_angle(yaw), normalize_angle(pitch))


def angular_difference(angle_a: float, angle_b: float) -> float:
    return normalize_angle(angle_b - angle_a)


def crosshair_target_error(view_yaw: float, view_pitch: float, target_yaw: float, target_pitch: float) -> tuple[float, float]:
    yaw_error = angular_difference(view_yaw, target_yaw)
    pitch_error = angular_difference(view_pitch, target_pitch)
    return (yaw_error, pitch_error)


def angular_distance(view_yaw: float, view_pitch: float, target_yaw: float, target_pitch: float) -> float:
    yaw_error, pitch_error = crosshair_target_error(view_yaw, view_pitch, target_yaw, target_pitch)
    return math.hypot(yaw_error, pitch_error)


def crosshair_to_target_distance(player_position: tuple[float, float, float], view_yaw: float, view_pitch: float, target_position: tuple[float, float, float]) -> float:
    target_yaw, target_pitch = direction_to_angles(player_position, target_position)
    return angular_distance(view_yaw, view_pitch, target_yaw, target_pitch)


def angular_velocity(previous_yaw: float, previous_pitch: float, current_yaw: float, current_pitch: float, delta_time: float) -> tuple[float, float]:
    if delta_time <= 0:
        raise ValueError('delta_time must be greater than zero')

    yaw_delta = angular_difference(previous_yaw, current_yaw)
    pitch_delta = angular_difference(previous_pitch, current_pitch)
    return (yaw_delta / delta_time, pitch_delta / delta_time)


def angular_speed(yaw_velocity: float, pitch_velocity: float) -> float:
    return math.hypot(yaw_velocity, pitch_velocity)


def angular_acceleration(previous_yaw_velocity: float, previous_pitch_velocity: float, current_yaw_velocity: float, current_pitch_velocity: float, delta_time: float) -> tuple[float, float]:
    if delta_time <= 0:
        raise ValueError('delta_time must be greater than zero')

    return ((current_yaw_velocity - previous_yaw_velocity) / delta_time, (current_pitch_velocity - previous_pitch_velocity) / delta_time)


def angular_acceleration_magnitude(yaw_acceleration: float, pitch_acceleration: float) -> float:
    return math.hypot(yaw_acceleration, pitch_acceleration)


def find_target_acquisition(angular_distances: list[float], threshold: float=3.0, min_consecutive_samples: int=2) -> int | None:
    if threshold < 0:
        raise ValueError('threshold must be non-negative')

    if min_consecutive_samples < 1:
        raise ValueError('min_consecutive_samples must be at least 1')

    consecutive = 0

    for index, distance in enumerate(angular_distances):
        if distance <= threshold:
            consecutive += 1

            if consecutive >= min_consecutive_samples:
                return index - min_consecutive_samples + 1
        else:
            consecutive = 0

    return None


def reaction_time(stimulus_index: int, response_index: int, sample_interval: float) -> float:
    if stimulus_index < 0 or response_index < 0:
        raise ValueError('indices must be non-negative')

    if response_index < stimulus_index:
        raise ValueError('response cannot occur before stimulus')

    if sample_interval <= 0:
        raise ValueError('sample_interval must be greater than zero')

    return (response_index - stimulus_index) * sample_interval


def find_aim_response(angular_distances: list[float], start_index: int, min_improvement: float=0.5, min_consecutive_samples: int=2) -> int | None:
    if start_index < 0:
        raise ValueError('start_index must be non-negative')

    if min_improvement < 0:
        raise ValueError('min_improvement must be non-negative')

    if min_consecutive_samples < 1:
        raise ValueError('min_consecutive_samples must be at least 1')

    if start_index >= len(angular_distances):
        return None

    consecutive = 0

    for index in range(start_index + 1, len(angular_distances)):
        improvement = angular_distances[index - 1] - angular_distances[index]

        if improvement >= min_improvement:
            consecutive += 1

            if consecutive >= min_consecutive_samples:
                return index - min_consecutive_samples + 1
        else:
            consecutive = 0

    return None


def mean_tracking_error(angular_distances: list[float]) -> float:
    if not angular_distances:
        raise ValueError('angular_distances must not be empty')

    return sum(angular_distances) / len(angular_distances)


def max_tracking_error(angular_distances: list[float]) -> float:
    if not angular_distances:
        raise ValueError('angular_distances must not be empty')

    return max(angular_distances)


def tracking_error_std(angular_distances: list[float]) -> float:
    if not angular_distances:
        raise ValueError('angular_distances must not be empty')

    mean = mean_tracking_error(angular_distances)
    variance = sum(((distance - mean) ** 2 for distance in angular_distances)) / len(angular_distances)
    return math.sqrt(variance)


def tracking_time_on_target_ratio(angular_distances: list[float], threshold: float=3.0) -> float:
    if not angular_distances:
        raise ValueError('angular_distances must not be empty')

    if threshold < 0:
        raise ValueError('threshold must be non-negative')

    on_target = sum((distance <= threshold for distance in angular_distances))
    return on_target / len(angular_distances)


def count_aim_corrections(angular_distances: list[float], min_change: float=0.1) -> int:
    if min_change < 0:
        raise ValueError('min_change must be non-negative')

    if len(angular_distances) < 3:
        return 0

    corrections = 0
    previous_direction = 0

    for index in range(1, len(angular_distances)):
        delta = angular_distances[index] - angular_distances[index - 1]

        if abs(delta) < min_change:
            continue

        current_direction = 1 if delta > 0 else -1

        if previous_direction != 0 and current_direction != previous_direction:
            corrections += 1

        previous_direction = current_direction

    return corrections


def find_potential_overshoots(angular_distances: list[float], proximity_threshold: float=5.0, min_departure: float=1.0) -> list[int]:
    if proximity_threshold < 0:
        raise ValueError('proximity_threshold must be non-negative')

    if min_departure < 0:
        raise ValueError('min_departure must be non-negative')

    overshoots = []

    for index in range(1, len(angular_distances) - 1):
        previous_distance = angular_distances[index - 1]
        current_distance = angular_distances[index]
        next_distance = angular_distances[index + 1]
        approached = current_distance < previous_distance
        departed = next_distance - current_distance >= min_departure
        close_to_target = current_distance <= proximity_threshold

        if approached and departed and close_to_target:
            overshoots.append(index)

    return overshoots


def find_potential_aim_snaps(angular_distances: list[float], angular_speeds: list[float], timestamps: list[float], start_distance_threshold: float=10.0, target_distance_threshold: float=5.0, min_angular_speed: float=200.0, max_duration: float=0.15) -> list[tuple[int, int]]:
    if not len(angular_distances) == len(angular_speeds) == len(timestamps):
        raise ValueError('angular_distances, angular_speeds and timestamps must have the same length')

    if any((timestamps[index] < timestamps[index - 1] for index in range(1, len(timestamps)))):
        raise ValueError('timestamps must be ordered')

    if start_distance_threshold < 0:
        raise ValueError('start_distance_threshold must be non-negative')

    if target_distance_threshold < 0:
        raise ValueError('target_distance_threshold must be non-negative')

    if min_angular_speed < 0:
        raise ValueError('min_angular_speed must be non-negative')

    if max_duration <= 0:
        raise ValueError('max_duration must be greater than zero')

    snaps = []

    for end_index in range(1, len(angular_distances)):
        if angular_distances[end_index] > target_distance_threshold:
            continue

        if angular_distances[end_index - 1] <= target_distance_threshold:
            continue

        for start_index in range(end_index):
            duration = timestamps[end_index] - timestamps[start_index]

            if duration > max_duration:
                continue

            if angular_distances[start_index] < start_distance_threshold:
                continue

            peak_speed = max(angular_speeds[start_index:end_index + 1])

            if peak_speed < min_angular_speed:
                continue

            snaps.append((start_index, end_index))
            break

    return snaps


def associate_shots_with_aim_sequences(sequence_windows: list[tuple[int, int]], sample_ticks: list[int], shot_ticks: list[int], max_tick_distance: int=2) -> list[AimSequence]:
    if max_tick_distance < 0:
        raise ValueError('max_tick_distance must be non-negative')

    sequences = []

    for start_index, end_index in sequence_windows:
        if start_index < 0 or end_index < 0 or start_index >= len(sample_ticks) or (end_index >= len(sample_ticks)):
            raise ValueError('sequence index out of range')

        if start_index > end_index:
            raise ValueError('sequence start cannot occur after sequence end')

        start_tick = sample_ticks[start_index]
        end_tick = sample_ticks[end_index]
        associated_shot_tick = None

        for shot_tick in shot_ticks:
            if start_tick <= shot_tick <= end_tick + max_tick_distance:
                associated_shot_tick = shot_tick
                break

        sequences.append(AimSequence(start_index=start_index, end_index=end_index, shot_tick=associated_shot_tick))

    return sequences
