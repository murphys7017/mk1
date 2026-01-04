import time
from typing import Any
from LocalModelFunc import LocalModelFunc
from MessageModel import ChatMessage
from PerceptionSystem.TextAnalyze import TextAnalyze
class PerceptionSystem:
    def __init__(self):
        self.local_llm = LocalModelFunc()
        self.text_analyz = TextAnalyze(self.local_llm)


    def analyze(self, input_data: Any) -> ChatMessage|None:
        if input_data.get("media_type") == "text":
            return self.text_analyz.textAnalysz(input_data.get("content"))
        return None