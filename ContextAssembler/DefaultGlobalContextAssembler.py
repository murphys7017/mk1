from typing import List
from ChatStateSystem.ChatStateSystem import ChatStateSystem
from ContextAssembler.GlobalContextAssembler import GlobalContextAssembler
from DataClass.ChatMessage import ChatMessage
from typing import Any

from DataClass.TagType import TagType
from MemorySystem.MemorySystem import MemorySystem
from RawChatHistory.RawChatHistory import RawChatHistory
from SystemPrompt import SystemPrompt
from tools import tools


class DefaultGlobalContextAssembler(GlobalContextAssembler):

    def __init__(
        self,
        memory_system: MemorySystem,
        chat_state_system: ChatStateSystem,
        system_prompt: SystemPrompt,
        raw_history: RawChatHistory,
        history_window: int,
       
    ):
        self.memory_system = memory_system
        self.chat_state_system = chat_state_system
        self.history_window = history_window
        self.raw_history = raw_history
        self.system_prompt = system_prompt

    def build_messages(
        self
    ) -> list[dict[str, Any]]:
        
        memory_system_prompt = self.memory_system.assemble()
        chat_state_prompt = self.chat_state_system.assemble()

        prompt = f"""
                {memory_system_prompt}
                {chat_state_prompt}

                <{TagType.RESPONSE_PROTOCOL_TAG}>
                {self.system_prompt.getPrompt(TagType.RESPONSE_PROTOCOL_TAG)}
                <\{TagType.RESPONSE_PROTOCOL_TAG}>
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