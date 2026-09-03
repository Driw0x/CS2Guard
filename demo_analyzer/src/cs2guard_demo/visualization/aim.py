import matplotlib.pyplot as plt


def plot_aim_trajectory(sample_ticks: list[int], angular_distances: list[float], shot_ticks: list[int] | None=None, hit_ticks: list[int] | None=None, overshoot_ticks: list[int] | None=None, snap_windows: list[tuple[int, int]] | None=None, title: str='Aim trajectory', show: bool=True) -> None:
    if len(sample_ticks) != len(angular_distances):
        raise ValueError('sample_ticks and angular_distances must have the same length')

    if not sample_ticks:
        raise ValueError('aim trajectory cannot be empty')

    plt.figure(figsize=(11, 6))
    plt.plot(sample_ticks, angular_distances, marker='o', label='Crosshair-to-target distance')

    if shot_ticks:
        for index, shot_tick in enumerate(shot_ticks):
            plt.axvline(x=shot_tick, linestyle='--', label='Shot' if index == 0 else None)

    if hit_ticks:
        first_hit = True

        for hit_tick in hit_ticks:
            if hit_tick not in sample_ticks:
                continue

            sample_index = sample_ticks.index(hit_tick)
            plt.scatter([hit_tick], [angular_distances[sample_index]], marker='X', s=120, zorder=5, label='Hit' if first_hit else None)
            first_hit = False

    if overshoot_ticks:
        for index, overshoot_tick in enumerate(overshoot_ticks):
            if overshoot_tick not in sample_ticks:
                continue

            sample_index = sample_ticks.index(overshoot_tick)
            plt.scatter([overshoot_tick], [angular_distances[sample_index]], marker='x', s=100, label='Potential overshoot' if index == 0 else None)

    if snap_windows:
        for index, (start_tick, end_tick) in enumerate(snap_windows):
            plt.axvspan(start_tick, end_tick, alpha=0.15, label='Potential snap' if index == 0 else None)

    plt.xlabel('Game tick')
    plt.ylabel('Angular distance (degrees)')
    plt.title(title)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    if show:
        plt.show()

    plt.close()
