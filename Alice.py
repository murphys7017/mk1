import time
from typing import Any
from openai import OpenAI
from ChatStateSystem import DefaultChatStateSystem
from ChatStateSystem.ChatStateSystem import ChatStateSystem
from ContextAssembler.DefaultGlobalContextAssembler import DefaultGlobalContextAssembler
from EventBus import EventBus
from LLM.LLMManagement import LLMManagement
from DataClass.ChatMessage import ChatMessage
from PerceptionSystem.PerceptionSystem import PerceptionSystem
from MemorySystem.MemorySystem import MemorySystem
from loguru import logger

from PostTurnProcessor import PostTurnProcessor
from RawChatHistory.RawChatHistory import RawChatHistory
from RawChatHistory.SqlitManagementSystem import SqlitManagementSystem
from SystemPrompt import SystemPrompt

class Alice:
    """ Alice 聊天机器人主类
    包含感知系统和记忆系统
    
    pipline:
    用户多模态输入 -> 感知系统分析 -> 记忆系统构建消息 -> LLM生成响应 -> 返回响应 -> 更新记忆系统 

    """
    def __init__(self,client, 
                 history_window=20, 
                 dialogue_window=4,
                 min_raw_for_summary=4,
                 default_history_length=100, 
                 default_dialogue_length=20 , 
                 db_path="chat_history.db" , 
                 db_echo=True,
                 **kwargs):
        self.history_window = history_window
        self.dialogue_window = dialogue_window
        self.min_raw_for_summary = min_raw_for_summary

        self.llm_management = LLMManagement()
        self.system_prompt = SystemPrompt()
        self.event_bus = EventBus()
        self.post_tuen_processor = PostTurnProcessor(
            
            self.llm_management, 
            self.event_bus)


        self.perception_system = PerceptionSystem(self.llm_management)

        

        
        self.raw_history = RawChatHistory(
                history_length= default_history_length, 
                dialogue_length= default_dialogue_length , 
                db_path= db_path, 
                echo= db_echo,
        )


        self.chat_state_system = DefaultChatStateSystem(
            llm_management=self.llm_management,
            system_prompt=self.system_prompt,
            raw_history=self.raw_history,
            history_window=self.history_window,
        )

        


        self.memory_system = MemorySystem(
            self.history_window, self.dialogue_window, self.min_raw_for_summary,
            self.raw_history, self.llm_management
        )


        self.assembler = DefaultGlobalContextAssembler(
            memory_system=self.memory_system,  # 后续设置
            chat_state_system=self.chat_state_system,  # 后续设置
            system_prompt=self.system_prompt,
            raw_history=self.raw_history,  # 后续设置
            history_window=self.history_window,
            dialogue_window=self.dialogue_window,
        )


    
        self.client = client

    def aggregated_input(self, user_inputs: list[ChatMessage]) -> ChatMessage:
        """
        简单聚合多个用户输入为一个输入
        目前仅返回最后一个输入，后续可改为更复杂的聚合逻辑
        """
        return user_inputs[-1]
    async def process_input(self, user_inputs: dict[str, Any]) -> ChatMessage:
        messages = await self.perception_system.analyze(user_inputs)
        logger.debug(f"Perceived messages: {messages}")
        if messages is None or len(messages) == 0:
            logger.warning("输入分析失败，将使用原始文本输入")
            if "text" not in user_inputs:
                return ChatMessage(
                    role="system", content="抱歉，我无法理解您的输入。",
                    timestamp=int(round(time.time() * 1000)),
                    timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    media_type="text",
                    )
            else:
                messages = [ChatMessage(
                    role="user", content=user_inputs["text"],
                    timestamp=int(round(time.time() * 1000)),
                    timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    media_type="text",
                    )]
        aggregated_input = self.aggregated_input(messages)
        return aggregated_input
    
    async def respond(self, user_inputs: dict[str, Any]) -> str:
        """
        生成对用户输入的响应
        """
        user_input = await self.process_input(user_inputs)
        self.raw_history.addMessage(user_input)
        logger.debug(f"User input added to history: {user_input}")
        messages = self.assembler.build_messages()
        logger.debug(f"Built messages for response: {messages}")

        response = self.client.respond(messages)
        logger.debug(f"Alice response: {response}")
        self.raw_history.addMessage(ChatMessage(
                role="assistant", content=response,
                timestamp=int(round(time.time() * 1000)),
                timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                media_type="text",
                ))
        
        return response
    
