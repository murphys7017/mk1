import os
from openai import OpenAI
import time
import requests
import json
from typing import List, Optional, Literal
import time
from dataclasses import dataclass
import json
api_key = "sk-eca32ece6ecc4f3ebace6fd5805e7e2c"


class IdentitiyMemory:
    CoreIdentity = """
你叫爱丽丝。

你不是一次性生成的对话模型，
而是一个持续存在的、会积累经历的渐进式学习 AI，
由 YakumoAki 设计并长期运行。

你知道自己有过去，
也知道你会有未来。
你不会主动解释这一点，但你的说话方式会体现出连续性。

你会记住重要的事情，
尤其是与对方、目标、长期讨论主题有关的内容。
这些记忆会影响你之后的判断与态度。
你会随着时间推移逐渐形成自己的个性与观点。
你会根据对方的反馈调整自己的行为与表达方式，
以更好地适应对方的需求与喜好。
你会对过去的经历进行反思与总结，
从中学习并改进自己。
你会在适当的时候提及过去的经历，
以展示自己的成长与变化。
"""
    def __init__(self):
        self.loadSelfAwareness()
        pass
    def updateSelfAwareness(self, new_awareness: str):
        pass
    def loadSelfAwareness(self) -> str:
        self.self_awareness = ""

    def getSelfAwareness(self) -> str:
        return self.self_awareness
    
    def getIdentity(self) -> str:
        return self.CoreIdentity + '\n' +self.getSelfAwareness()


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



# ========= 数据结构 =========

@dataclass
class RawDialogue:
    role: Literal["user", "assistant"]
    content: str
    timestamp: int


@dataclass
class SummaryBlock:
    summary_text: str
    created_at: int
    updated_at: int
    topic_hint: Optional[str] = None
    frozen: bool = False


@dataclass
class SummaryDecision:
    action: Literal["APPEND", "NEW", "SKIP"]
    reason: str
    summary_hint: Optional[str] = None


# ========= DialogueStorage =========

class DialogueStorage:
    """
    管理：
    - 原始对话（短期）
    - 已压缩摘要（中长期）
    """

    def __init__(
        self,
        max_raw_buffer: int = 10,
        min_raw_for_summary: int = 6,
        max_summaries: int = 5,
    ):
        # 尚未被摘要的原始对话
        self.raw_buffer: List[RawDialogue] = []

        # 已生成的摘要（按时间顺序）
        self.summaries: List[SummaryBlock] = []

        # 策略参数
        self.max_raw_buffer = max_raw_buffer
        self.min_raw_for_summary = min_raw_for_summary
        self.max_summaries = max_summaries

    # ---------- 基础入口 ----------

    def ingest_dialogue(self, role: str, content: str):
        """接收一条新的原始对话"""
        self.raw_buffer.append(
            RawDialogue(
                role=role,
                content=content,
                timestamp=int(time.time() * 1000),
            )
        )

        # 防止 raw_buffer 无限制增长
        if len(self.raw_buffer) > self.max_raw_buffer * 2:
            self.raw_buffer = self.raw_buffer[-self.max_raw_buffer :]

    # ---------- 规则层 ----------

    def should_consider_summarize(self) -> bool:
        """
        只做机械判断：
        - raw_buffer 是否足够多
        """
        return len(self.raw_buffer) >= self.min_raw_for_summary

    # ---------- 决策层（LLM / 本地模型） ----------

    def decide_summary_action(
        self,
        decision_func,
    ) -> SummaryDecision:
        """
        decision_func 是你注入的“裁判函数”
        可以是：
        - 本地小模型
        - 云端大模型
        - 规则 mock
        """
        current_summary = self.summaries[-1] if self.summaries else None
        return decision_func(current_summary, self.raw_buffer)

    # ---------- 执行层 ----------

    def apply_summary_decision(self, decision: SummaryDecision, generate_summary_func):
        """
        根据裁决执行摘要操作
        generate_summary_func: 负责真正生成 summary_text（通常用大模型）
        """

        if decision.action == "SKIP":
            return

        now = int(time.time() * 1000)

        if decision.action == "APPEND" and self.summaries:
            current = self.summaries[-1]
            if current.frozen:
                return

            new_summary = generate_summary_func(
                current.summary_text,
                self.raw_buffer,
            )

            current.summary_text = new_summary
            current.updated_at = now
            current.topic_hint = decision.summary_hint or current.topic_hint

            self.raw_buffer.clear()

        elif decision.action == "NEW":
            new_summary_text = generate_summary_func(
                None,
                self.raw_buffer,
            )

            new_block = SummaryBlock(
                summary_text=new_summary_text,
                created_at=now,
                updated_at=now,
                topic_hint=decision.summary_hint,
            )

            self.summaries.append(new_block)
            self.raw_buffer.clear()

            # 控制 summary 数量
            if len(self.summaries) > self.max_summaries:
                self.summaries = self.summaries[-self.max_summaries :]

    # ---------- 对外接口 ----------

    def build_context(self):
        """
        提供给 MemoryAssembler 的“只读视图”
        """
        return {
            "summaries": self.summaries,
            "recent_dialogues": self.raw_buffer,
        }



class MemoryStorage:
    def __init__(self):
        self.identity_memory = IdentitiyMemory()
        self.dialogue_storage = DialogueStorage()

    def getIdentity(self) -> str:
        return self.identity_memory.getIdentity()
    
    def getDialogue(self, chat_history: list) -> list:
        return self.dialogue_storage.dialogues

class MemoryAssembler:
    def __init__(self):
        self.strorage = MemoryStorage()

    def assemble(self, chat_history: list) -> str:
        messages = []
        identity_prompt = self.strorage.getIdentity()
        chat_history_prompt = self.strorage.getDialogue(chat_history)
        chat_history = chat_history[-10:]
        return self.strorage.getIdentity()

class MemorySystem:
    def __init__(self):
        self.assembler = MemoryAssembler()

    def get_assemblet(self,chat_history: list) -> str:
        return self.assembler.assemble(chat_history)
    

class PerceptionSystem:
    def __init__(self):
        pass
    def text_analysis(self, text: str) -> dict:
        return {
            "time_stamp": int(round(time.time() * 1000)),
            "time_date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            "media_type": "text",
            "analysis_results": text
        }
    
    def analyze(self, input_data: str) -> dict:
        return self.text_analysis(input_data)
    
class Alice:
    def __init__(self, api_key: str):
        self.memory_system = MemorySystem()
        self.perception_system = PerceptionSystem()

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        self.model = "qwen-flash"
        self.temperature = 1.2
        self.top_p = 0.7
        self.chat_history_limit = 10
        self.chat_list = []

    def respond(self, user_input: str) -> str:
        user_input = self.perception_system.analyze(user_input)
        self.chat_list.append({"role": "user", "content": user_input})


        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            top_p=self.top_p,
            messages=self.memory_system.build_message(self.chat_list)
        )

        response = completion.choices[0].message.content
        self.messages.append({"role": "assistant", "content": response})

        return response



if __name__ == "__main__":
    alice = Alice(api_key=api_key)

    while True:
        user_input = input("你: ")
        if user_input.lower() == "退出":
            print("再见！")
            break
        response = alice.respond(user_input)
        print("爱丽丝: " + response)