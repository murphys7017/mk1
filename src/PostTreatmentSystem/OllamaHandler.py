
import time
from typing import Any

from loguru import logger
from DataClass.AnalyzeResult import AnalyzeResult
from LLM.LLMManagement import LLMManagement
from DataClass.ChatMessage import ChatMessage
from PerceptionSystem.AnalyzeAbstract import Analyze
from PostTreatmentSystem.HandlerAbstract import Handler
from RawChatHistory.RawChatHistory import RawChatHistory
from SystemPrompt import SystemPrompt


class OllamaHandler(Handler):
    def __init__(self, llm_management: LLMManagement):
        self.llm_management = llm_management
    
    def handler(self, raw_history: RawChatHistory, res: dict[str,Any]) -> dict[str, Any]:
        input_data = raw_history.getHistory(1)[-1].content
        analysis_results = self.text_analysis(input_data)
        res['ollama'] = analysis_results
        return res
    

    def text_analysis(self, text: str) -> dict[str, Any]:
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
        res = {}
        if data is None :
            return {}
        
        res["is_question"] = data.get("is_question", None)
        res["is_self_reference"] = data.get("is_self_reference", None)
        res["emotion_cues"] = data.get("emotional_cues", [])
        logger.debug(f"OllamaAnalyze text_analysis result: {res}")
        return res

