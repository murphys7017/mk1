import time
from typing import Any
from LocalModelFunc import LocalModelFunc
from MessageModel import ChatMessage
class PerceptionSystem:
    def __init__(self):
        self.local_llm = LocalModelFunc()
    def text_analysis(self, text: str) -> ChatMessage:
        analysis_results = self.local_llm.text_analysis(text)
        return ChatMessage(
            role="user",
            content=text,
            timestamp=int(round(time.time() * 1000)),
            timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            media_type="text",
            extra=analysis_results
        )
    
    def analyze(self, input_data: Any) -> ChatMessage:
        return self.text_analysis(input_data)