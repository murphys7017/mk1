from abc import ABC, abstractmethod
from typing import Any


class Agent(ABC):
    @abstractmethod
    def respond(self,messages) -> Any:
        pass