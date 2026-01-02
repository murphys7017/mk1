import requests
import json
class SystemPrompt:
    def judge_dialogue_summary_model():
        return "qwen3:1.7b"
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
  "need_summary": true | false,
  "action": "append" | "new" | "none"
}

        """
    
    def summarize_dialogue_model():
        return "qwen3:4b"
    def summarize_dialogue_prompt():
        return """
你是一个长期记忆摘要系统。

你的任务是将多轮对话压缩为一段「可长期保存的记忆」。

摘要要求：
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

    def judge_dialogue_summary(
        self,
        previous_summary: str,
        dialogues: list[dict]
    ) -> dict:
        """
        使用 1.5B 裁判模型（Ollama）
        """

        # === 1. 构造输入文本（一定要短） ===
        dialogue_text = []
        for d in dialogues[-6:]:  # 永远不要给太多
            role = d.get("role", "unknown")
            content = d.get("content", "")
            dialogue_text.append(f"{role}: {content}")

        input_text = f"""
【已有摘要】
{previous_summary if previous_summary else "（无）"}

【最近对话】
{chr(10).join(dialogue_text)}
"""
        input_text = self.sys_prompt.judge_dialogue_summary_prompt() + input_text

        # === 2. 调用 Ollama（示意） ===
        decision = self._call_ollama_judge(input_text)


        return decision

    # ------------------------
    # 内部 Ollama 调用（占位）
    # ------------------------
    def _call_ollama_judge(self, prompt: str) -> str:
        """
        实际实现中：
        - model: qwen3:1.7b
        - temperature: 0
        - top_p: 1
        """

        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.sys_prompt.judge_dialogue_summary_model(),
            "prompt": prompt,
            "options": {
                "temperature": 0,
                "top_p": 1
            }
        }
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            # Ollama API 返回内容可能在 'response' 或 'message' 字段
            output = data.get("response") or data.get("message") or ""
            # 尝试提取 JSON
            start = output.find('{')
            end = output.rfind('}')
            if start != -1 and end != -1:
                output = output[start:end+1]
            # 验证 JSON
            try:
                decision = json.loads(output)

                # 强校验
                if not isinstance(decision.get("need_summary"), bool):
                    raise ValueError("need_summary invalid")

                if decision.get("action") not in ("append", "new", "none"):
                    raise ValueError("action invalid")

                return decision
                

            except Exception:
                return {"need_summary": False, "action": "none"}
        except Exception:
            return {"need_summary": False, "action": "none"}


    """
    本地模型能力集合
    所有 Ollama / 本地模型调用统一从这里走
    """

    # ===== 对话记忆相关 =====

    def summarize_dialogue(
        self,
        previous_summary: str,
        dialogues: list[dict]
    ) -> str:
        """
        使用 3B 摘要模型（Ollama）
        返回长期记忆友好的摘要文本
        """

        # === 1. 构造对话文本（可比裁判稍多） ===
        dialogue_lines = []
        for d in dialogues[-10:]:
            role = d.get("role", "unknown")
            content = d.get("content", "")
            dialogue_lines.append(f"{role}: {content}")

        input_text = f"""
【已有摘要】
{previous_summary if previous_summary else "（无）"}

【未摘要对话】
{chr(10).join(dialogue_lines)}

请根据以上内容，生成新的长期记忆摘要。
"""
        input_text = self.sys_prompt.summarize_dialogue_prompt() + input_text
        # === 2. 调用 Ollama ===
        summary_text = self._call_ollama_summarizer(input_text)

        # === 3. 后处理（非常重要） ===
        summary_text = summary_text.strip()

        # 兜底：防止模型输出空文本或胡言乱语
        if not summary_text or len(summary_text) < 5:
            return previous_summary

        # 防止模型偷偷变第一人称
        summary_text = self._sanitize_summary(summary_text)

        return summary_text

    # ------------------------
    # 内部方法（占位）
    # ------------------------
    def _call_ollama_summarizer(self, prompt: str) -> str:
        """
        使用 Ollama 调用 qwen3-3b-summary
        """

        url = "http://localhost:11434/api/generate"

        payload = {
            "model": self.sys_prompt.summarize_dialogue_model(),
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.25,
                "top_p": 0.9,
                "repeat_penalty": 1.05,
                "num_predict": 256
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()

            return data.get("response", "").strip()

        except Exception as e:
            # ⚠️ 兜底：摘要失败时绝不能炸系统
            print(f"[Ollama Summarizer Error] {e}")
            return ""
        
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