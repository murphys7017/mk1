
from typing import Any
from dataclasses import dataclass


@dataclass
class ChatEvent:
    event_type: str
    turn_id: int
    timestamp: int
    data: Any