import time
from openai import OpenAI
from MessageModel import ChatMessage
from PerceptionSystem.PerceptionSystem import PerceptionSystem
from MemorySystem.MemorySystem import MemorySystem
from loguru import logger

from RawChatHistory import RawChatHistory
class Alice:
    def __init__(self, api_key: str):
        self.raw_history = RawChatHistory()
        if self.raw_history is None:
            logger.error("RawChatHistory is not initialized.")
            raise ValueError("RawChatHistory must be provided to initialize MemorySystem.")
        self.memory_system = MemorySystem(self.raw_history)
        self.perception_system = PerceptionSystem()

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        self.model = "qwen-plus"
        self.temperature = 1.2
        self.top_p = 0.7
        self.chat_history_limit = 10
        self.chat_list = []

    def respond(self, user_input: str) -> str:
        user_input = self.perception_system.analyze(user_input)
        logger.info(f"Perceived input: {user_input}")

        messages = self.memory_system.buildMessages(user_input)



        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            messages=messages
        )

        response = completion.choices[0].message.content
        self.raw_history.add_message(ChatMessage(
            role="assistant", content=response,
            timestamp=int(round(time.time() * 1000)),
            timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            media_type="text",
            ))

        return response
