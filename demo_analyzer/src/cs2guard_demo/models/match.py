from dataclasses import dataclass, field
from .player import Player
from .round import Round
from .tick import Tick
from .event import Event
@dataclass


class Match:
    map_name: str
    patch_version: str
    demo_version: str
    players: list[Player] = field(default_factory=list)
    rounds: list[Round] = field(default_factory=list)
    ticks: list[Tick] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
