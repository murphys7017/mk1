import requests
import json
from typing import Any
from loguru import logger
from MessageModel import ChatMessage, DialogueMessage
from SystemPrompt import SystemPrompt
class LocalModelFunc:
    def __init__(self):
        pass

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
            
            # 尝试提取 JSON
            start = output.find('{')
            end = output.rfind('}')
            if start != -1 and end != -1:
                output = output[start:end+1]
            try:
                decision = json.loads(output)
                return decision
            except Exception:
                return {}
        except Exception as e:
            print(f"[Ollama API Error] {e}")
            return {}

    def _call_openai_api(self, prompt: str, model: str, options: dict | None = None) -> dict:
        """
        通用OpenAI本地模型API调用函数。
        参数：
            prompt: 输入文本
            model: 模型名称
            options: 推理参数字典
            timeout: 超时时间（秒）
            stream: 是否流式
        返回：
            dict，包含 response/message 字段内容
        """
        import os
        from openai import OpenAI

        client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
            api_key="sk-eca32ece6ecc4f3ebace6fd5805e7e2c",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        model = 'qwen-plus'
        completion = client.chat.completions.create(
            # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
            model=model,
            response_format ={"type": "json_object"},
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            top_p=1,
        )
        res = json.loads(completion.choices[0].message.content) # type: ignore
        return res
