from loguru import logger
from logging_config import timeit_logger
import requests
from typing import Any

from LLM.LLMChatAbstract import Chat

class OllamaChat(Chat):
    def __init__(self):
        self.model = "qwen3:8b"  # 默认模型名称，可根据需要修改
        self.options = {
            "temperature": 0.7,
            "top_p": 0.9
        }
    def supportModel(self) -> list[str]:
        return ["qwen3:8b", "qwen3:1.7b", "qwen3:4b"]
    def respond(self, messages):
        return self.chat(messages, self.model, self.options)

    @timeit_logger(name="OllamaChat.chat", level="DEBUG")
    def chat(self, messages: list[dict], model: str, options: dict | None = None) -> dict:
        return self._call_ollama_api(messages, model, options)
    
    def _call_ollama_api(self, messages: list[dict], model: str, options: dict[str, Any] | None = None) -> Any:
        """
        通用Ollama本地模型API调用函数。
        参数：
            prompt: 输入文本
            model: 模型名称
            options: 推理参数字典
            timeout: 超时时间（秒）
            stream: 是否流式
        返回：
            dict，包含 response/message 字段内容
        """
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": options or {}
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            output = data.get("response") or data.get("message") or ""
            if isinstance(output, dict):
                output = output.get("content", "")
            # 去除思考内
            return output
        except Exception as e:
            logger.error(f"[Ollama API Error] {e}")
            return self.failuredResponse()
    def failuredResponse(self) -> dict:
        return {}