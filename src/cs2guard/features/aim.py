import math


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