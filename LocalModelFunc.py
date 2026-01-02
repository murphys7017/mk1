import requests
import json

from MessageModel import DialogueMessage
class SystemPrompt:
    @staticmethod
    def split_buffer_by_topic_continuation_model():
        return "qwen3:1.7b"
    @staticmethod
    def split_buffer_by_topic_continuation_prompt():
        return """
你是一个对话连贯性分析器。请判断新对话轮次中有多少轮延续了已有摘要的话题。

【已有摘要】
{current_summary}

【新对话轮次】（从第0轮开始编号）
{dialogue_turns}

请回答：最多前几轮属于同一话题？（若第1轮就切换，回答0；若全部延续，回答总轮数）

只输出一个整数x，{"index": x }，不要任何其他文字。
x必须是一个非负整数，且不能大于新对话轮次的总数。

"""
    @staticmethod
    def text_analysis_model():
        return "qwen3:1.7b"
    @staticmethod
    def text_analysis_prompt():
        return """
        你是一个客观的文本观察器。请严格根据用户输入的字面内容，回答以下问题：

        1. 是否包含明确的问题（包括疑问句、反问句、设问句）？是 / 否。
        2. 是否提及“你”、“您”、“爱丽丝”或“AI”？是 / 否。
        3. 提到了哪些具体实体或主题词？（如人名、地点、事物、概念，例如：“下雨天”、“Python”、“昨天的会议”）
        4. 出现了哪些表达情绪或态度的词语？（如“讨厌”、“希望”、“烦”、“太棒了”）

        仅输出 JSON，不要任何解释或额外文本。使用以下格式：

        {
        "is_question": true,
        "is_self_reference": false,
        "mentioned_entities": ["词1", "词2"],
        "emotional_cues": ["词3"]
        }

        用户输入：{input}
        """
    @staticmethod
    def judge_dialogue_summary_model():
        return "qwen3:1.7b"
    @staticmethod
    def judge_dialogue_summary_prompt():
        return """
你是一个对话记忆裁判系统。

你的任务不是生成对话内容，
而是判断「最近的对话是否需要被摘要，以及如何处理」。

你必须遵守：
- 不进行创作
- 不补充细节
- 不做情绪渲染
- 不解释原因
- 只返回 JSON

你将收到：
1. 已有摘要（可能为空）
2. 尚未摘要的最近对话列表

你需要判断：
- 是否需要生成摘要
- 如果需要，是合并到已有摘要，还是生成新的摘要

判断依据：
- 是否出现新的长期话题
- 是否出现稳定偏好、关系变化、目标、承诺
- 是否只是闲聊 / 短期问答

返回格式必须严格如下：
{
  "need_summary": true | false
}

        """
    
    @staticmethod
    def summarize_dialogue_model():
        return "qwen3:4b"
    @staticmethod
    def summarize_dialogue_prompt():
        return """
你是一个长期记忆摘要系统。

你的任务是将多轮对话压缩为一段「可长期保存的记忆」。

摘要要求：
- 如果【已有摘要】不为空，则在此基础上更新和扩展
- 使用第三人称
- 不使用修辞
- 不编造未出现的信息
- 不包含对话原文
- 保留以下内容（如存在）：
  - 稳定话题
  - 用户偏好
  - 关系变化
  - 明确目标或承诺
  - 情绪倾向（仅在明显时）

风格要求：
- 中性
- 简洁
- 可被未来系统直接使用
        """

class LocalModelFunc:
    def __init__(self):
        self.sys_prompt = SystemPrompt()
    def split_buffer_by_topic_continuation(self, current_summary: str, dialogue_turns: str) -> int:
        input_text = self.sys_prompt.split_buffer_by_topic_continuation_prompt().format(
            current_summary=current_summary,
            dialogue_turns=dialogue_turns
        )
        model = self.sys_prompt.split_buffer_by_topic_continuation_model()
        options = {"temperature": 0, "top_p": 1}
        data = self._call_openai_api(input_text, model, options)
        return data.get("index", 0)

    def text_analysis(self, text: str) -> dict:
        """
        使用 1.7B 文本分析模型（Ollama）
        """

        input_text = self.sys_prompt.text_analysis_prompt()
        input_text = input_text.replace("{input}", text)

        # === 2. 调用 Ollama（示意） ===
        model = self.sys_prompt.text_analysis_model()
        options = {"temperature": 0, "top_p": 1}

        data = self._call_openai_api(input_text, model, options)
        if data is None:
            return {
                "is_question": False,
                "is_self_reference": False,
                "mentioned_entities": [],
                "emotional_cues": []
            }
        else:
            return data

    def judge_dialogue_summary(
        self,
        summary: str,
        dialogues: str
    ) -> dict:
        """
        使用 1.5B 裁判模型（Ollama）
        """

        # === 1. 构造输入文本（一定要短） ===

        input_text = f"""

【已有摘要】
{summary if summary else "（无）"}

【最近对话】
{dialogues}
"""
        input_text = self.sys_prompt.judge_dialogue_summary_prompt() + input_text

        # === 2. 调用 Ollama（示意） ===
        model = self.sys_prompt.judge_dialogue_summary_model()
        options = {"temperature": 0, "top_p": 1}

        data = self._call_openai_api(input_text, model, options)
        if data is None:
            return {"need_summary": False}
        else:
            return data

    # ------------------------
    # 内部 Ollama 调用（占位）
    # ------------------------
    def _call_ollama_api(self, prompt: str, model: str, options: dict = None) -> dict:
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
                return None
        except Exception as e:
            print(f"[Ollama API Error] {e}")
            return None

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
        summary: DialogueMessage,
        dialogues: str
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
        input_text = self.sys_prompt.summarize_dialogue_prompt() + input_text
        # === 2. 调用 OpenAI ===
        model = self.sys_prompt.summarize_dialogue_model()
        options = {
            "temperature": 0.25,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            "num_predict": 256
        }
        data = self._call_openai_api(input_text, model, options)
        summary_text = (data.get("summary")).strip()
    

        # === 3. 后处理（非常重要） ===
        summary_text = summary_text.strip()

        # 兜底：防止模型输出空文本或胡言乱语
        if not summary_text or len(summary_text) < 5:
            return summary

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


    # ===== 自我状态相关（未来） =====

    def update_self_awareness(
        self,
        old_state: str,
        recent_summaries: list[str]
    ) -> str:
        """
        可选：使用 8B
        更新 Alice 的自我状态
        """
        pass

    # ===== 安全 / 监控（未来） =====

    def detect_persona_drift(
        self,
        identity_prompt: str,
        summaries: list[str]
    ) -> bool:
        """
        判断人格是否发生偏移
        """
        pass