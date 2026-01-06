from abc import ABC, abstractmethod
from typing import Any
from DataClass.ChatMessage import ChatMessage


class GlobalContextAssembler(ABC):
    """
    负责构建 LLM 调用所需的完整上下文
    """

    @abstractmethod
    def build_messages(
        self
    ) -> list[dict[str, Any]]:
        """
        recent_messages:
            最近 N 条原始对话消息（user / assistant）

        return:
            OpenAI / Qwen 兼容的 messages 列表
            [
              {"role": "system", "content": "..."},
              {"role": "user", "content": "..."},
              ...
            ]
        """
        pass
    
