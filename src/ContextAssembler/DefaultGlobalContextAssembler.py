from typing import List

from loguru import logger
from ChatStateSystem.ChatStateSystem import ChatStateSystem
from ContextAssembler.GlobalContextAssembler import GlobalContextAssembler
from DataClass.ChatMessage import ChatMessage
from typing import Any

from DataClass.TagType import TagType
from MemorySystem.MemorySystem import MemorySystem
from RawChatHistory.RawChatHistory import RawChatHistory
from SystemPrompt import SystemPrompt
from tools.PromptBuilder import PromptBuilder
from tools.tools import tools


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
        self.user_inputs: List[ChatMessage] = []

    def build_messages(
        self,
        user_input: ChatMessage
    ) -> list[dict[str, Any]]:
        self.user_inputs.append(user_input)
        self.user_inputs = self.user_inputs[-3:]

        system_prompt = self.memory_system.assemble()
        chat_state_prompt = self.chat_state_system.assemble()
        system_prompt.include(chat_state_prompt) 

        analyze_prompt = PromptBuilder(TagType.ANALYZE_TAG)

        for msg in self.user_inputs:
            anl = msg.analyze_result
            if anl is not None:
                analyze_prompt.include(anl.analyze_result_to_prompt())
        system_prompt.include(analyze_prompt)



        response_protocol = PromptBuilder(TagType.RESPONSE_PROTOCOL_TAG)
        resp_prompt = self.system_prompt.getPrompt(TagType.RESPONSE_PROTOCOL_TAG)
        for line in resp_prompt.lines:
            response_protocol.add(line)
        system_prompt.include(response_protocol)
        logger.debug("Final system prompt build completed.")


        messages = []

        messages.append({
            "role": "system",
            "content": system_prompt.build()
        })

        # 原始对话放最后
        buffer = self.raw_history.getHistory(self.history_window)
        for msg in buffer:
            messages.append(msg.buildMessage())

        return messages