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
            processd_inputs.append(
                self.perception_system.analyze(user_input)
            )
        aggregated_input = self.aggregated_input(processd_inputs)
        logger.info(f"Perceived input: {aggregated_input}")
        messages = self.memory_system.buildMessages(aggregated_input)
        
        return messages
    
    def respond(self, user_inputs: list[Any]) -> str:
        """
        生成对用户输入的响应
        """
        messages = self.process_input(user_inputs)
        response = self.client.respond(messages)
        logger.info(f"Alice response: {response}")
        return response
    
