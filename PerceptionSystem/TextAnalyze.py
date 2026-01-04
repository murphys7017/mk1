
import time
from LocalModelFunc import LocalModelFunc
from MessageModel import ChatMessage
from SystemPrompt import SystemPrompt


class TextAnalyze:
    def __init__(self, local_model_func: LocalModelFunc):
        self.local_model_func = local_model_func
    
    def textAnalysz(self, text: str) -> ChatMessage:
        analysis_results = self.text_analysis(text)
        return ChatMessage(
            role="user",
            content=text,
            timestamp=int(round(time.time() * 1000)),
            timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            media_type="text",
            extra=analysis_results
        )
    

    def text_analysis(self, text: str) -> dict:
        """
        使用 1.7B 文本分析模型（Ollama）
        """

        input_text = SystemPrompt.text_analysis_prompt()
        input_text = input_text.replace("{input}", text)

        # === 2. 调用 Ollama（示意） ===
        model = SystemPrompt.text_analysis_model()
        options = {"temperature": 0, "top_p": 1}

        data = self.local_model_func._call_ollama_api(input_text, model, options)
        if data is {} or data is None:
            return {
                "is_question": False,
                "is_self_reference": False,
                "mentioned_entities": [],
                "emotional_cues": []
            }
        else:
            return data
