
import time

from loguru import logger
from LLM.LLMManagement import LLMManagement
from DataClass.ChatMessage import ChatMessage
from PerceptionSystem.Analyzeabstract import Analyze
from SystemPrompt import SystemPrompt


class OllamaAnalyze(Analyze):
    def __init__(self, llm_management: LLMManagement):
        self.llm_management = llm_management
    
    def analyze(self, input_data: str) -> dict:
        analysis_results = self.text_analysis(input_data)
        return analysis_results
    

    def text_analysis(self, text: str) -> dict:
        """
        使用 1.7B 文本分析模型（Ollama）
        """
        options = {"temperature": 0, "top_p": 1}

        data = self.llm_management.generate(
            prompt_name="text_analysis",
            options=options,
            input=text
        )
        logger.debug(f"Text Analysis Response: {data}")
        # data = None

        if data is {} or data is None:
            return {
                "is_question": False,
                "is_self_reference": False,
                "mentioned_entities": [],
                "emotional_cues": []
            }
        else:
            return data
