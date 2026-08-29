from dataclasses import dataclass


@dataclass
class AimSequence:
    start_index: int
    end_index: int
    shot_tick: int | None = None