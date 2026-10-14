import matplotlib
import pytest
matplotlib.use('Agg')
from cs2guard_demo.visualization import plot_aim_trajectory


def test_plot_aim_trajectory_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        plot_aim_trajectory(sample_ticks=[100, 101], angular_distances=[1.0], show=False)


def test_plot_aim_trajectory_rejects_empty_data():
    with pytest.raises(ValueError):
        plot_aim_trajectory(sample_ticks=[], angular_distances=[], show=False)


def test_plot_aim_trajectory_accepts_valid_data():
    plot_aim_trajectory(sample_ticks=[100, 101, 102], angular_distances=[5.0, 3.0, 1.0], show=False)


def test_plot_aim_trajectory_accepts_all_markers():
    plot_aim_trajectory(sample_ticks=[100, 101, 102, 103], angular_distances=[10.0, 4.0, 2.0, 5.0], shot_ticks=[102], hit_ticks=[102], overshoot_ticks=[102], snap_windows=[(100, 102)], title='Test aim trajectory', show=False)


def test_plot_aim_trajectory_exports_image_with_reference_label(tmp_path, monkeypatch):
    import matplotlib.pyplot as plt

    labels = []
    original_plot = plt.plot

    def capture_plot(*args, **kwargs):
        labels.append(kwargs['label'])
        return original_plot(*args, **kwargs)

    monkeypatch.setattr(plt, 'plot', capture_plot)
    output_path = tmp_path / 'aim.png'
    plot_aim_trajectory([100, 101, 102], [5.0, 3.0, 0.0], show=False,
                        output_path=output_path, distance_label='Distance to shot aim direction')

    assert output_path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert labels == ['Distance to shot aim direction']
    assert not plt.get_fignums()
