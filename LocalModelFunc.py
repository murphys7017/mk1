import requests
import json
from typing import Any
from loguru import logger
from MessageModel import ChatMessage, DialogueMessage
from SystemPrompt import SystemPrompt
class LocalModelFunc:
    def __init__(self):
        pass


    def text_analysis(self, text: str) -> dict:
        """
        使用 1.7B 文本分析模型（Ollama）
        """

        input_text = SystemPrompt.text_analysis_prompt()
        input_text = input_text.replace("{input}", text)

        # === 2. 调用 Ollama（示意） ===
        model = SystemPrompt.text_analysis_model()
        options = {"temperature": 0, "top_p": 1}

        data = self._call_ollama_api(input_text, model, options)
        if data is {} or data is None:
            return {
                "is_question": False,
                "is_self_reference": False,
                "mentioned_entities": [],
                "emotional_cues": []
            }
        else:
            return data


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

    def _call_openai_api(self, prompt: str, model: str, options: dict = None) -> dict:
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
        res = json.loads(completion.choices[0].message.content)
        return res




    """
    本地模型能力集合
    所有 Ollama / 本地模型调用统一从这里走
    """
    def summarize_dialogue(
        self,
        summary: DialogueMessage|None,
        dialogues: list[ChatMessage]
    ) -> str:
        """
        使用 3B 摘要模型（Ollama）
        返回长期记忆友好的摘要文本
        """
        dialogues_text = " "
        i = 1
        for msg in dialogues:
                dialogues_text += f"[{i}] role:{msg.role} content:{msg.content}\n"
                i += 1

        input_text = f"""
【已有摘要】
{summary.summary if summary else "（无）"}

【未摘要对话】
{dialogues_text}

请根据以上内容，生成新的长期记忆摘要。
返回要求：
{"summary": "文本内容"}
"""
        input_text = SystemPrompt.summarize_dialogue_prompt() + input_text
        # === 2. 调用 OpenAI ===
        model = SystemPrompt.summarize_dialogue_model()
        options = {
            "temperature": 0.25,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            "num_predict": 256
        }
        data = self._call_openai_api(input_text, model, options)
        summary_text = (data.get("summary", summary.summary if summary else "（无）")).strip()
    

        # === 3. 后处理（非常重要） ===
        summary_text = summary_text.strip()

        # 兜底：防止模型输出空文本或胡言乱语
        if not summary_text or len(summary_text) < 5:
            return summary.summary if summary else "（无）"

        # 防止模型偷偷变第一人称
        summary_text = self._sanitize_summary(summary_text)

        return summary_text


    def _sanitize_summary(self, text: str) -> str:
        """
        简单防护：
        - 移除第一人称
        - 移除明显情绪化语句
        """

        forbidden = ["我认为", "我觉得", "我感到", "我正在"]
        for word in forbidden:
            text = text.replace(word, "")

        return text
