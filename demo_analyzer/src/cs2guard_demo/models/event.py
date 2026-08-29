from dataclasses import dataclass
from typing import Any


@dataclass
class Event:
    tick: int
    event_type: str
    data: dict[str, Any]