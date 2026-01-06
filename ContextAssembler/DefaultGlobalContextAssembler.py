from typing import List
from ContextAssembler.GlobalContextAssembler import GlobalContextAssembler
from DataClass.ChatMessage import ChatMessage
from typing import Any

from tools import tools


class DefaultGlobalContextAssembler(GlobalContextAssembler):

    def __init__(
        self,
        memory_storage,
        chat_state_system,
        raw_history,
        response_protocol: str,
        history_window: int = 20,
        max_dialogue_summary: int = 3
    ):
        self.memory_storage = memory_storage
        self.chat_state_system = chat_state_system
        self.response_protocol = response_protocol
        self.history_window = history_window
        self.max_dialogue_summary = max_dialogue_summary
        self.raw_history = raw_history

    def build_messages(
        self
    ) -> list[dict[str, Any]]:
        
        memory_system_prompt = self.memory_storage.assemble()
        chat_state_prompt = self.chat_state_system.assemble()

        prompt = f"""
                {memory_system_prompt}
                {chat_state_prompt}
        """


        messages = []

        messages.append({
            "role": "system",
            "content": tools.normalizeBlock(prompt)
        })

        # 原始对话放最后
        buffer = self.raw_history.getHistory(self.history_window)
        for msg in buffer:
            messages.append(msg.buildMessage())

        return messages