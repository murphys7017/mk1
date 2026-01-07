from abc import ABC, abstractmethod
from typing import Any

from LLM.LLMManagement import LLMManagement
from DataClass.ChatState import ChatState
from RawChatHistory.RawChatHistory import RawChatHistory
from SystemPrompt import SystemPrompt
from tools import tools
from loguru import logger

class ChatStateSystem(ABC):
    """
    管理：
    - 原始对话（短期）
    - 已压缩摘要（中长期）
    """


    @abstractmethod
    def getState(self) -> ChatState:
        pass
    @abstractmethod
    def checkAndUpdateState(self, turn_id: int):
        pass
    @abstractmethod
    def assemble(self) -> str:
        pass