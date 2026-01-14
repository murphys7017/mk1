from abc import ABC, abstractmethod
from typing import Any

from DataClass.AnalyzeResult import AnalyzeResult
from RawChatHistory.RawChatHistory import RawChatHistory

class Handler(ABC):
    @abstractmethod
    def handler(self,raw_history: RawChatHistory, res: dict[str,Any]) -> dict[str,Any]:
        pass