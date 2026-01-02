import time
from typing import List, Optional, Literal
import time
from dataclasses import dataclass
import json

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
