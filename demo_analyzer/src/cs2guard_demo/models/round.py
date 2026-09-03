from dataclasses import dataclass
@dataclass


class Round:
    number: int
    start_tick: int
    end_tick: int
    winner: str
    reason: str
