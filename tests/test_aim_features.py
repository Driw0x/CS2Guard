import math

from cs2guard.features.aim import (
    normalize_angle,
    direction_to_angles,
    angular_difference,
    crosshair_target_error,
    angular_distance,
    crosshair_to_target_distance,
)


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

    assert math.isclose(yaw, 0.0, abs_tol=1e-6)
    assert math.isclose(pitch, 0.0, abs_tol=1e-6)


def test_direction_to_angles_right():
    source = (0.0, 0.0, 0.0)
    target = (0.0, 100.0, 0.0)

    yaw, pitch = direction_to_angles(source, target)

    assert math.isclose(yaw, 90.0, abs_tol=1e-6)
    assert math.isclose(pitch, 0.0, abs_tol=1e-6)


def test_direction_to_angles_up():
    source = (0.0, 0.0, 0.0)
    target = (100.0, 0.0, 100.0)

    yaw, pitch = direction_to_angles(source, target)

    assert math.isclose(yaw, 0.0, abs_tol=1e-6)
    assert math.isclose(pitch, -45.0, abs_tol=1e-6)


def test_angular_difference_basic():
    assert math.isclose(
        angular_difference(10.0, 20.0),
        10.0,
        abs_tol=1e-6,
    )

    assert math.isclose(
        angular_difference(20.0, 10.0),
        -10.0,
        abs_tol=1e-6,
    )


def test_angular_difference_wraparound():
    assert math.isclose(
        angular_difference(179.0, -179.0),
        2.0,
        abs_tol=1e-6,
    )

    assert math.isclose(
        angular_difference(-179.0, 179.0),
        -2.0,
        abs_tol=1e-6,
    )


def test_crosshair_target_error():
    yaw_error, pitch_error = crosshair_target_error(
        view_yaw=10.0,
        view_pitch=5.0,
        target_yaw=15.0,
        target_pitch=2.0,
    )

    assert math.isclose(yaw_error, 5.0, abs_tol=1e-6)
    assert math.isclose(pitch_error, -3.0, abs_tol=1e-6)


def test_angular_distance():
    distance = angular_distance(
        view_yaw=0.0,
        view_pitch=0.0,
        target_yaw=3.0,
        target_pitch=4.0,
    )

    assert math.isclose(distance, 5.0, abs_tol=1e-6)


def test_crosshair_to_target_distance_perfect_alignment():
    distance = crosshair_to_target_distance(
        player_position=(0.0, 0.0, 0.0),
        view_yaw=0.0,
        view_pitch=0.0,
        target_position=(100.0, 0.0, 0.0),
    )

    assert math.isclose(distance, 0.0, abs_tol=1e-6)


def test_crosshair_to_target_distance_90_degrees():
    distance = crosshair_to_target_distance(
        player_position=(0.0, 0.0, 0.0),
        view_yaw=0.0,
        view_pitch=0.0,
        target_position=(0.0, 100.0, 0.0),
    )

    assert math.isclose(distance, 90.0, abs_tol=1e-6)