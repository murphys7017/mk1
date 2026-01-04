import time
from typing import Any
from openai import OpenAI
from LocalModelFunc import LocalModelFunc
from MessageModel import ChatMessage
from PerceptionSystem.PerceptionSystem import PerceptionSystem
from MemorySystem.MemorySystem import MemorySystem
from loguru import logger

from RawChatHistory import RawChatHistory

class Alice:
    def __init__(self, api_key: str,client):
        self.raw_history = RawChatHistory()

        if self.raw_history is None:
            logger.error("RawChatHistory is not initialized.")
            raise ValueError("RawChatHistory must be provided to initialize MemorySystem.")
        
        self.local_model_func = LocalModelFunc()

        self.perception_system = PerceptionSystem()

        self.memory_system = MemorySystem(self.raw_history, self.local_model_func)

    
        self.client = client

    def aggregated_input(self, user_inputs: list[ChatMessage]) -> ChatMessage:
        """
        简单聚合多个用户输入为一个输入
        目前仅返回最后一个输入，后续可改为更复杂的聚合逻辑
        """
        return user_inputs[-1]

    def process_input(self, user_inputs: list[Any]):
        """
        处理用户多模态输入，调用感知系统进行分析
        返回聚合后的输入
        """
        processd_inputs = []
        for user_input in user_inputs:
            res = self.perception_system.analyze(user_input)
            if res:
                processd_inputs.append(res)
        if len(processd_inputs) == 0:
            logger.warning("No valid input perceived.")
            return None
        aggregated_input = self.aggregated_input(processd_inputs)
        logger.info(f"Perceived input: {aggregated_input}")

        self.raw_history.addMessage(aggregated_input)
        self.memory_system.strorage.checkAndUpdateState()

        messages = self.memory_system.buildMessages(aggregated_input)
        
        return messages
    
    def respond(self, user_inputs: list[Any]) -> str:
        """
        生成对用户输入的响应
        """
        messages = self.process_input(user_inputs)
        logger.debug(f"Built messages for response: {messages}")
        if messages is None:
            return "抱歉，我无法理解您的输入。"
        else:
            response = self.client.respond(messages)
            logger.info(f"Alice response: {response}")
            self.raw_history.addMessage(ChatMessage(
                role="assistant", content=response,
                timestamp=int(round(time.time() * 1000)),
                timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                media_type="text",
                ))
        return response
    
