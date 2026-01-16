from typing import List

from logging_config import logger
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
        analysis_window: int = 3,
       
    ):
        self.memory_system = memory_system
        self.chat_state_system = chat_state_system
        self.history_window = history_window
        self.raw_history = raw_history
        self.system_prompt = system_prompt
        self.analysis_window = analysis_window

    def build_messages(
        self
    ) -> list[dict[str, Any]]:
        
        # query context from memory system / chat state system /other modules
 
        # 总体 system prompt 构建流程：
        system_prompt = PromptBuilder()


        # 记忆系统部分
        world_core_prompt = self.memory_system.assembleWorldCore()
        memory_prompt = PromptBuilder(TagType.MEMORY_SYSTEM_TAG)
        identity_prompt = self.memory_system.assembleIdentity()
        short_memory_prompt = self.memory_system.assembleShortMemory()
        # query info 


        memory_prompt.include(identity_prompt)
        memory_prompt.include(short_memory_prompt)

        # 对话状态分析部分
        chat_state_prompt = self.chat_state_system.assemble()
        

        analyze_prompt = PromptBuilder(TagType.ANALYZE_TAG)

        for msg in self.raw_history.getHistory(self.analysis_window):
            anl = msg.analyze_result
            if anl is not None:
                analyze_prompt.include(anl.analyze_result_to_prompt())
        

        system_prompt.include(world_core_prompt)
        system_prompt.include(memory_prompt)
        system_prompt.include(analyze_prompt)
        system_prompt.include(chat_state_prompt) 

        # 响应协议部分
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