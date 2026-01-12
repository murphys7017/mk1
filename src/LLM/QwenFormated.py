from LLM.LLMAbstract import LLM
from typing import Any
import requests
from loguru import logger
import json
import os
from openai import OpenAI
class QwenFormated(LLM):
    def generate(self, prompt: str, model: str, options: dict | None = None) -> dict:
        return self._call_openai_api(prompt, model, options)
    
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


        client = OpenAI(
            # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
            api_key= os.environ.get("OPENAI_API_KEY") ,
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
    def failuredResponse(self) -> dict:
        return {}
