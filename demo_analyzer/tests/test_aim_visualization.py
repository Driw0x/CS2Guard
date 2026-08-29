import matplotlib
import pytest

matplotlib.use("Agg")

from cs2guard_demo.visualization.aim import (
    plot_aim_trajectory,
)


def test_plot_aim_trajectory_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        plot_aim_trajectory(
            sample_ticks=[100, 101],
            angular_distances=[1.0],
            show=False,
        )


def test_plot_aim_trajectory_rejects_empty_data():
    with pytest.raises(ValueError):
        plot_aim_trajectory(
            sample_ticks=[],
            angular_distances=[],
            show=False,
        )


def test_plot_aim_trajectory_accepts_valid_data():
    plot_aim_trajectory(
        sample_ticks=[100, 101, 102],
        angular_distances=[5.0, 3.0, 1.0],
        show=False,
    )


def test_plot_aim_trajectory_accepts_all_markers():
    plot_aim_trajectory(
        sample_ticks=[
            100,
            101,
            102,
            103,
        ],
        angular_distances=[
            10.0,
            4.0,
            2.0,
            5.0,
        ],
        shot_ticks=[102],
        hit_ticks=[102],
        overshoot_ticks=[102],
        snap_windows=[
            (100, 102),
        ],
        title="Test aim trajectory",
        show=False,
    )