from abc import ABC, abstractmethod
from typing import Any

class BaseStore(ABC):

    # ---- DB / history wrappers (统一通过 MemoryStorage 访问 RawChatHistory) ----
    @abstractmethod
    def add_history(self, history) -> int:
        """Add a ChatMessage to history via RawChatHistory and return turn_id."""
        pass
    @abstractmethod
    def get_history(self, length: int = -1) -> list:
        pass
    @abstractmethod
    def get_history_by_role(self, role: str, length: int = -1, sender_id: int | None = None) -> list:
        pass
    @abstractmethod
    def delete_history_by_id(self, chat_turn_id: int):
        pass

    @abstractmethod
    def update_history(self, obj):
        pass
    @abstractmethod
    def get_history_by_id(self, id: int) -> Any | None:
        pass
    