from dataclasses import dataclass


@dataclass
class Tick:
    tick: int
    steamid: int
    player_name: str
    team: str

    x: float
    y: float
    z: float

    yaw: float
    pitch: float