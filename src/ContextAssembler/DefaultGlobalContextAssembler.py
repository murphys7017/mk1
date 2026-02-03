from typing import List

from logging_config import logger, timeit_logger
from ChatStateSystem.ChatStateSystem import ChatStateSystem
from ContextAssembler.GlobalContextAssembler import GlobalContextAssembler
from DataClass.ChatMessage import ChatMessage
from typing import Any

from DataClass.TagType import TagType
from MemorySystem.MemorySystem import MemorySystem
from SystemPrompt import SystemPrompt
from tools.PromptBuilder import PromptBuilder


class DefaultGlobalContextAssembler(GlobalContextAssembler):

    def __init__(
        self,
        memory_system: MemorySystem,
        chat_state_system: ChatStateSystem,
        system_prompt: SystemPrompt,
        history_window: int,
        analysis_window: int = 3,
       
    ):
        self.memory_system = memory_system
        self.chat_state_system = chat_state_system
        self.history_window = history_window
        self.system_prompt = system_prompt
        self.analysis_window = analysis_window

    @timeit_logger(name="DefaultGlobalContextAssembler.build_messages", level="DEBUG")
    def build_messages(
        self
    ) -> list[dict[str, Any]]:
        
        # query context from memory system / chat state system /other modules
 
        # 总体 system prompt 构建流程：
        system_prompt = PromptBuilder()


        
        world_core_prompt = self.memory_system.assembleWorldCore()
        system_prompt.include(world_core_prompt)

        # 记忆系统部分
        memory_prompt = PromptBuilder(TagType.MEMORY_SYSTEM_TAG)
        identity_prompt = self.memory_system.assembleIdentity()
        short_memory_prompt = self.memory_system.assembleShortMemory()
        # query info 

        memory_prompt.include(identity_prompt)
        memory_prompt.include(short_memory_prompt)
        system_prompt.include(memory_prompt)




        

        # 用户协议部分
        user_protocol = PromptBuilder(TagType.IDENTITY_PROTOCOL_TAG)
        iden_prompt = self.system_prompt.getPrompt(TagType.IDENTITY_PROTOCOL_TAG)
        for line in iden_prompt.lines:
            user_protocol.add(line)

        system_prompt.include(user_protocol)

        
        # 分析结果部分
        analyze_prompt = PromptBuilder(TagType.ANALYZE_TAG)

        for msg in self.memory_system.storage.get_history_by_role("user", self.analysis_window, sender_id=1):
            b = PromptBuilder(f"User Message ID {msg.chat_turn_id}")
            b.add(msg.buildContent())
            b.add(f"TimeDate: {msg.timedate}")
            anl = msg.analyze_result
            if anl is not None:
                b.include(anl.analyze_result_to_prompt())
            analyze_prompt.include(b)

        system_prompt.include(analyze_prompt)

        # 对话状态分析部分
        chat_state_prompt = self.chat_state_system.assemble()
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
        buffer = self.memory_system.storage.get_history(self.history_window)
        for msg in buffer:
            messages.append(msg.buildMessage())

        return messages