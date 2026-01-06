import time
from typing import Any
from openai import OpenAI
from LLM.LLMManagement import LLMManagement
from MessageModel import ChatMessage
from PerceptionSystem.PerceptionSystem import PerceptionSystem
from MemorySystem.MemorySystem import MemorySystem
from loguru import logger

from RawChatHistory.RawChatHistory import RawChatHistory
from RawChatHistory.SqlitManagementSystem import SqlitManagementSystem
from SystemPrompt import SystemPrompt

class Alice:
    """ Alice 聊天机器人主类
    包含感知系统和记忆系统
    
    pipline:
    用户多模态输入 -> 感知系统分析 -> 记忆系统构建消息 -> LLM生成响应 -> 返回响应 -> 更新记忆系统 

    """
    def __init__(self, api_key: str,client, **kwargs):
        self.llm_management = LLMManagement()
        self.system_prompt = SystemPrompt()

        self.history_manager = SqlitManagementSystem(
                                                    kwargs.get("db_path", "chat_history.db"), 
                                                    echo=kwargs.get("echo", False), 
                                                   )
        self.raw_history = RawChatHistory(
                                        self.history_manager,
                                        history_length=kwargs.get("history_length", 100), 
                                        dialogue_length=kwargs.get("dialogue_length", 10)
                                        )

        self.perception_system = PerceptionSystem(self.llm_management)

        self.memory_system = MemorySystem(self.raw_history, self.llm_management)

    
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

        messages = [] # global context assember

        logger.debug(f"Built messages for response: {messages}")

        response = self.client.respond(messages)
        logger.info(f"Alice response: {response}")
        self.raw_history.addMessage(ChatMessage(
                role="assistant", content=response,
                timestamp=int(round(time.time() * 1000)),
                timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                media_type="text",
                ))
        return response
    
