import math
from ..models.aim_sequence import AimSequence


def normalize_angle(angle: float) -> float:
    """
    Normalize an angle to the [-180, 180) range.
    """
    return (angle + 180.0) % 360.0 - 180.0


def direction_to_angles(
    source: tuple[float, float, float],
    target: tuple[float, float, float],
) -> tuple[float, float]:
    """
    Compute the yaw and pitch required to look from source to target.

    Returns:
        tuple[float, float]: (yaw, pitch) in degrees.
    """
    dx = target[0] - source[0]
    dy = target[1] - source[1]
    dz = target[2] - source[2]

    horizontal_distance = math.hypot(dx, dy)

    yaw = math.degrees(math.atan2(dy, dx))
    pitch = -math.degrees(math.atan2(dz, horizontal_distance))

    return normalize_angle(yaw), normalize_angle(pitch)


def angular_difference(angle_a: float, angle_b: float) -> float:
    """
    Compute the smallest signed angular difference from angle_a to angle_b.
    """
    return normalize_angle(angle_b - angle_a)


def crosshair_target_error(
    view_yaw: float,
    view_pitch: float,
    target_yaw: float,
    target_pitch: float,
) -> tuple[float, float]:
    """
    Compute yaw and pitch errors between the current crosshair direction
    and the target direction.

    Returns:
        tuple[float, float]: (yaw_error, pitch_error) in degrees.
    """
    yaw_error = angular_difference(view_yaw, target_yaw)
    pitch_error = angular_difference(view_pitch, target_pitch)

    return yaw_error, pitch_error


def angular_distance(
    view_yaw: float,
    view_pitch: float,
    target_yaw: float,
    target_pitch: float,
) -> float:
    """
    Compute an approximate angular distance between the crosshair
    and the target direction.

    Returns:
        float: Angular distance in degrees.
    """
    yaw_error, pitch_error = crosshair_target_error(
        view_yaw,
        view_pitch,
        target_yaw,
        target_pitch,
    )

    return math.hypot(yaw_error, pitch_error)


def crosshair_to_target_distance(
    player_position: tuple[float, float, float],
    view_yaw: float,
    view_pitch: float,
    target_position: tuple[float, float, float],
) -> float:
    """
    Compute the angular distance between a player's crosshair and a target.

    Args:
        player_position: Player position (x, y, z).
        view_yaw: Current player yaw in degrees.
        view_pitch: Current player pitch in degrees.
        target_position: Target position (x, y, z).

    Returns:
        float: Angular distance to the target in degrees.
    """
    target_yaw, target_pitch = direction_to_angles(
        player_position,
        target_position,
    )

    return angular_distance(
        view_yaw,
        view_pitch,
        target_yaw,
        target_pitch,
    )

def angular_velocity(
    previous_yaw: float,
    previous_pitch: float,
    current_yaw: float,
    current_pitch: float,
    delta_time: float,
) -> tuple[float, float]:
    """
    Compute yaw and pitch angular velocities.

    Args:
        previous_yaw: Previous yaw angle in degrees.
        previous_pitch: Previous pitch angle in degrees.
        current_yaw: Current yaw angle in degrees.
        current_pitch: Current pitch angle in degrees.
        delta_time: Time between the two samples in seconds.

    Returns:
        tuple[float, float]: (yaw_velocity, pitch_velocity)
        in degrees per second.

    Raises:
        ValueError: If delta_time is not strictly positive.
    """
    if delta_time <= 0:
        raise ValueError("delta_time must be greater than zero")

    yaw_delta = angular_difference(previous_yaw, current_yaw)
    pitch_delta = angular_difference(previous_pitch, current_pitch)

    return (
        yaw_delta / delta_time,
        pitch_delta / delta_time,
    )

def angular_speed(
    yaw_velocity: float,
    pitch_velocity: float,
) -> float:
    """
    Compute the magnitude of an angular velocity.

    Returns:
        float: Angular speed in degrees per second.
    """
    return math.hypot(yaw_velocity, pitch_velocity)

def angular_acceleration(
    previous_yaw_velocity: float,
    previous_pitch_velocity: float,
    current_yaw_velocity: float,
    current_pitch_velocity: float,
    delta_time: float,
) -> tuple[float, float]:
    """
    Compute yaw and pitch angular accelerations.

    Args:
        previous_yaw_velocity: Previous yaw velocity in degrees per second.
        previous_pitch_velocity: Previous pitch velocity in degrees per second.
        current_yaw_velocity: Current yaw velocity in degrees per second.
        current_pitch_velocity: Current pitch velocity in degrees per second.
        delta_time: Time between velocity samples in seconds.

    Returns:
        tuple[float, float]: (yaw_acceleration, pitch_acceleration)
        in degrees per second squared.

    Raises:
        ValueError: If delta_time is not strictly positive.
    """
    if delta_time <= 0:
        raise ValueError("delta_time must be greater than zero")

    return (
        (current_yaw_velocity - previous_yaw_velocity) / delta_time,
        (current_pitch_velocity - previous_pitch_velocity) / delta_time,
    )

def angular_acceleration_magnitude(
    yaw_acceleration: float,
    pitch_acceleration: float,
) -> float:
    """
    Compute the magnitude of an angular acceleration.

    Returns:
        float: Angular acceleration magnitude in degrees per second squared.
    """
    return math.hypot(yaw_acceleration, pitch_acceleration)

def find_target_acquisition(
    angular_distances: list[float],
    threshold: float = 3.0,
    min_consecutive_samples: int = 2,
) -> int | None:
    """
    Find the first sample where a target is considered acquired.

    A target is acquired when the angular distance remains below or equal
    to the threshold for at least `min_consecutive_samples` consecutive
    samples.

    Args:
        angular_distances: Angular distance to the target for each sample.
        threshold: Maximum angular distance considered on target.
        min_consecutive_samples: Required number of consecutive samples
            below the threshold.

    Returns:
        Index of the first sample of the acquisition sequence,
        or None if the target is never acquired.

    Raises:
        ValueError: If threshold is negative or min_consecutive_samples
            is less than 1.
    """
    if threshold < 0:
        raise ValueError("threshold must be non-negative")

    if min_consecutive_samples < 1:
        raise ValueError("min_consecutive_samples must be at least 1")

    consecutive = 0

    for index, distance in enumerate(angular_distances):
        if distance <= threshold:
            consecutive += 1

            if consecutive >= min_consecutive_samples:
                return index - min_consecutive_samples + 1
        else:
            consecutive = 0

    return None

def reaction_time(
    stimulus_index: int,
    response_index: int,
    sample_interval: float,
) -> float:
    """
    Compute the reaction time between a stimulus and a response.

    Args:
        stimulus_index: Index where the stimulus starts.
        response_index: Index where the player starts responding.
        sample_interval: Time between samples in seconds.

    Returns:
        Reaction time in seconds.

    Raises:
        ValueError: If indices are invalid, the response occurs before
            the stimulus, or sample_interval is not strictly positive.
    """
    if stimulus_index < 0 or response_index < 0:
        raise ValueError("indices must be non-negative")

    if response_index < stimulus_index:
        raise ValueError("response cannot occur before stimulus")

    if sample_interval <= 0:
        raise ValueError("sample_interval must be greater than zero")

    return (response_index - stimulus_index) * sample_interval

def find_aim_response(
    angular_distances: list[float],
    start_index: int,
    min_improvement: float = 0.5,
    min_consecutive_samples: int = 2,
) -> int | None:
    """
    Find the first sample where the player starts consistently moving
    the crosshair toward the target.

    A response is detected when the angular distance decreases by at least
    `min_improvement` degrees for a required number of consecutive samples.

    Args:
        angular_distances: Angular distance to the target for each sample.
        start_index: Index from which to start searching for a response.
        min_improvement: Minimum decrease in angular distance between
            consecutive samples.
        min_consecutive_samples: Required number of consecutive improvements.

    Returns:
        Index of the first sample of the response sequence,
        or None if no response is found.

    Raises:
        ValueError: If parameters are invalid.
    """
    if start_index < 0:
        raise ValueError("start_index must be non-negative")

    if min_improvement < 0:
        raise ValueError("min_improvement must be non-negative")

    if min_consecutive_samples < 1:
        raise ValueError("min_consecutive_samples must be at least 1")

    if start_index >= len(angular_distances):
        return None

    consecutive = 0

    for index in range(start_index + 1, len(angular_distances)):
        improvement = (
            angular_distances[index - 1]
            - angular_distances[index]
        )

        if improvement >= min_improvement:
            consecutive += 1

            if consecutive >= min_consecutive_samples:
                return index - min_consecutive_samples + 1
        else:
            consecutive = 0

    return None

def mean_tracking_error(
    angular_distances: list[float],
) -> float:
    """
    Compute the mean angular tracking error.

    Args:
        angular_distances: Angular distances to the target in degrees.

    Returns:
        float: Mean tracking error in degrees.

    Raises:
        ValueError: If angular_distances is empty.
    """
    if not angular_distances:
        raise ValueError("angular_distances must not be empty")

    return sum(angular_distances) / len(angular_distances)


def max_tracking_error(
    angular_distances: list[float],
) -> float:
    """
    Compute the maximum angular tracking error.

    Args:
        angular_distances: Angular distances to the target in degrees.

    Returns:
        float: Maximum tracking error in degrees.

    Raises:
        ValueError: If angular_distances is empty.
    """
    if not angular_distances:
        raise ValueError("angular_distances must not be empty")

    return max(angular_distances)


def tracking_error_std(
    angular_distances: list[float],
) -> float:
    """
    Compute the population standard deviation of tracking error.

    Args:
        angular_distances: Angular distances to the target in degrees.

    Returns:
        float: Standard deviation of tracking error in degrees.

    Raises:
        ValueError: If angular_distances is empty.
    """
    if not angular_distances:
        raise ValueError("angular_distances must not be empty")

    mean = mean_tracking_error(angular_distances)

    variance = sum(
        (distance - mean) ** 2
        for distance in angular_distances
    ) / len(angular_distances)

    return math.sqrt(variance)

def tracking_time_on_target_ratio(
    angular_distances: list[float],
    threshold: float = 3.0,
) -> float:
    """
    Compute the ratio of samples where the crosshair stays within
    a given angular distance from the target.

    Args:
        angular_distances: Angular distances to the target in degrees.
        threshold: Maximum distance considered on target.

    Returns:
        float: Ratio between 0.0 and 1.0.

    Raises:
        ValueError: If angular_distances is empty or threshold is negative.
    """
    if not angular_distances:
        raise ValueError("angular_distances must not be empty")

    if threshold < 0:
        raise ValueError("threshold must be non-negative")

    on_target = sum(
        distance <= threshold
        for distance in angular_distances
    )

    return on_target / len(angular_distances)

def count_aim_corrections(
    angular_distances: list[float],
    min_change: float = 0.1,
) -> int:
    """
    Count changes in the direction of the crosshair movement relative
    to the target.

    A correction occurs when the angular distance changes from decreasing
    to increasing or from increasing to decreasing.

    Args:
        angular_distances: Angular distances to the target in degrees.
        min_change: Minimum distance change required to consider movement.

    Returns:
        Number of detected direction changes.

    Raises:
        ValueError: If min_change is negative.
    """
    if min_change < 0:
        raise ValueError("min_change must be non-negative")

    if len(angular_distances) < 3:
        return 0

    corrections = 0
    previous_direction = 0

    for index in range(1, len(angular_distances)):
        delta = (
            angular_distances[index]
            - angular_distances[index - 1]
        )

        if abs(delta) < min_change:
            continue

        current_direction = 1 if delta > 0 else -1

        if (
            previous_direction != 0
            and current_direction != previous_direction
        ):
            corrections += 1

        previous_direction = current_direction

    return corrections

def find_potential_overshoots(
    angular_distances: list[float],
    proximity_threshold: float = 5.0,
    min_departure: float = 1.0,
) -> list[int]:
    """
    Find potential overshoots in an angular-distance sequence.

    A potential overshoot is identified when the crosshair approaches
    the target, reaches a local minimum near the target, and then moves
    away by at least `min_departure`.

    Args:
        angular_distances: Angular distances to the target in degrees.
        proximity_threshold: Maximum local-minimum distance considered
            close enough to the target.
        min_departure: Minimum increase after the local minimum.

    Returns:
        Indices of potential overshoot points.

    Raises:
        ValueError: If thresholds are negative.
    """
    if proximity_threshold < 0:
        raise ValueError("proximity_threshold must be non-negative")

    if min_departure < 0:
        raise ValueError("min_departure must be non-negative")

    overshoots = []

    for index in range(1, len(angular_distances) - 1):
        previous_distance = angular_distances[index - 1]
        current_distance = angular_distances[index]
        next_distance = angular_distances[index + 1]

        approached = current_distance < previous_distance

        departed = (
            next_distance - current_distance
            >= min_departure
        )

        close_to_target = (
            current_distance <= proximity_threshold
        )

        if approached and departed and close_to_target:
            overshoots.append(index)

    return overshoots

def find_potential_aim_snaps(
    angular_distances: list[float],
    angular_speeds: list[float],
    timestamps: list[float],
    start_distance_threshold: float = 10.0,
    target_distance_threshold: float = 5.0,
    min_angular_speed: float = 200.0,
    max_duration: float = 0.15,
) -> list[tuple[int, int]]:
    """
    Find potential rapid aim movements toward a target.

    A potential snap is a short aiming sequence where:
    - the crosshair starts sufficiently far from the target;
    - it finishes close to the target;
    - the movement reaches a sufficiently high angular speed;
    - the movement happens within a limited duration.

    This function only identifies snap candidates.
    It does not classify cheats.

    Args:
        angular_distances:
            Angular distance to the target for each sample, in degrees.

        angular_speeds:
            Angular speed for each sample, in degrees per second.

        timestamps:
            Timestamp associated with each sample, in seconds.

        start_distance_threshold:
            Minimum angular distance required at the beginning of
            a candidate snap.

        target_distance_threshold:
            Maximum angular distance allowed at the end of
            a candidate snap.

        min_angular_speed:
            Minimum peak angular speed required during
            the candidate sequence.

        max_duration:
            Maximum duration of a candidate snap, in seconds.

    Returns:
        List of (start_index, end_index) candidate snap windows.

    Raises:
        ValueError:
            If the input lists have different lengths,
            timestamps are not ordered,
            or one of the thresholds is invalid.
    """
    if not (
        len(angular_distances)
        == len(angular_speeds)
        == len(timestamps)
    ):
        raise ValueError(
            "angular_distances, angular_speeds and timestamps "
            "must have the same length"
        )

    if any(
        timestamps[index] < timestamps[index - 1]
        for index in range(1, len(timestamps))
    ):
        raise ValueError("timestamps must be ordered")

    if start_distance_threshold < 0:
        raise ValueError(
            "start_distance_threshold must be non-negative"
        )

    if target_distance_threshold < 0:
        raise ValueError(
            "target_distance_threshold must be non-negative"
        )

    if min_angular_speed < 0:
        raise ValueError(
            "min_angular_speed must be non-negative"
        )

    if max_duration <= 0:
        raise ValueError(
            "max_duration must be greater than zero"
        )

    snaps = []

    for end_index in range(1, len(angular_distances)):
        # A snap candidate ends when the crosshair enters
        # the target proximity zone.
        if (
            angular_distances[end_index]
            > target_distance_threshold
        ):
            continue

        # Ignore samples that were already inside the target zone.
        if (
            angular_distances[end_index - 1]
            <= target_distance_threshold
        ):
            continue

        for start_index in range(end_index):
            duration = (
                timestamps[end_index]
                - timestamps[start_index]
            )

            if duration > max_duration:
                continue

            if (
                angular_distances[start_index]
                < start_distance_threshold
            ):
                continue

            peak_speed = max(
                angular_speeds[start_index:end_index + 1]
            )

            if peak_speed < min_angular_speed:
                continue

            snaps.append(
                (
                    start_index,
                    end_index,
                )
            )

            # Since we search from oldest to newest,
            # this is the earliest valid start point.
            break

    return snaps

def associate_shots_with_aim_sequences(
    sequence_windows: list[tuple[int, int]],
    sample_ticks: list[int],
    shot_ticks: list[int],
    max_tick_distance: int = 2,
) -> list[AimSequence]:
    """
    Associate shots with aim sequence windows.

    A shot is associated with a sequence if it occurs during the sequence
    or shortly after it, within `max_tick_distance`.

    Args:
        sequence_windows:
            List of (start_index, end_index) aim sequence windows.

        sample_ticks:
            Game tick corresponding to each aim sample.

        shot_ticks:
            Ticks where the player fired.

        max_tick_distance:
            Maximum number of ticks after the sequence end for a shot
            to still be associated with the sequence.

    Returns:
        AimSequence objects containing the associated shot tick,
        if one was found.

    Raises:
        ValueError:
            If max_tick_distance is negative or a sequence window
            contains invalid indices.
    """
    if max_tick_distance < 0:
        raise ValueError(
            "max_tick_distance must be non-negative"
        )

    sequences = []

    for start_index, end_index in sequence_windows:
        if (
            start_index < 0
            or end_index < 0
            or start_index >= len(sample_ticks)
            or end_index >= len(sample_ticks)
        ):
            raise ValueError(
                "sequence index out of range"
            )

        if start_index > end_index:
            raise ValueError(
                "sequence start cannot occur after sequence end"
            )

        start_tick = sample_ticks[start_index]
        end_tick = sample_ticks[end_index]

        associated_shot_tick = None

        for shot_tick in shot_ticks:
            if (
                start_tick
                <= shot_tick
                <= end_tick + max_tick_distance
            ):
                associated_shot_tick = shot_tick
                break

        sequences.append(
            AimSequence(
                start_index=start_index,
                end_index=end_index,
                shot_tick=associated_shot_tick,
            )
        )

    return sequences