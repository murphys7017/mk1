from LLM.LLMAbstract import LLM
from typing import Any
import requests
from loguru import logger
import json

class OllamaFormated(LLM):
    def generate(self, prompt: str, model: str, options: dict | None = None) -> dict:
        return self._call_ollama_api(prompt, model, options)
    def supportModel(self) -> list[str]:
        return ["qwen3:1.7b", "qwen3:4b"]
    def _call_ollama_api(self, prompt: str, model: str, options: dict[str, Any] | None = None) -> dict:
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
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": options or {}
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()

            data = response.json()
            output = data.get("response") or data.get("message") or ""
            logger.debug(f"Ollama API Raw Output: {output}")
            
            # 尝试提取 JSON
            start = output.find('{')
            end = output.rfind('}')
            if start != -1 and end != -1:
                output = output[start:end+1]
                logger.debug(f"Ollama API Extracted JSON: {output}")
            try:
                decision = json.loads(output)
                return decision
            except Exception:
                return {}
        except Exception as e:
            print(f"[Ollama API Error] {e}")
            return self.failuredResponse()
    def failuredResponse(self) -> dict:
        return {}