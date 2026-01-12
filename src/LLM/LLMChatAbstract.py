from abc import ABC, abstractmethod
from typing import List


class Chat(ABC):
    @abstractmethod
    def respond(self, messages) -> dict:
        pass
    @abstractmethod
    def chat(self, messages: list[dict], model: str, options: dict | None = None) -> dict:
        pass