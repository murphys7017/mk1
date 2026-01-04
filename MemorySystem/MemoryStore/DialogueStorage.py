import time
from typing import List, Optional, Literal
import time
from dataclasses import dataclass
import json

from LocalModelFunc import LocalModelFunc
from MemorySystem import MemoryPolicy
from RawChatHistory import RawChatHistory
from MessageModel import ChatMessage, DialogueMessage
from MemorySystem.MemoryPolicy import MemoryPolicy

from loguru import logger
from SystemPrompt import SystemPrompt
from tools import tools
@dataclass
class SummaryDecision:
    action: Literal["APPEND", "NEW", "SKIP"]
    reason: str
    summary_hint: Optional[str] = None


class DialogueStorage:
    """
    管理：
    - 原始对话（短期）
    - 已压缩摘要（中长期）
    """

    def __init__(
        self,
        raw_history: RawChatHistory,
        local_model_func: LocalModelFunc,
        policy: MemoryPolicy,
        # 最大长度
        max_raw_buffer: int = 50,
        # 达到该数量后检查是否需要摘要
        min_raw_for_summary: int = 4,
        history_window: int = 3,
        
    ):
        self.raw_history = raw_history

        # 尚未被摘要的原始对话
        self.raw_buffer: List[ChatMessage] = []

        # 已生成的摘要（按时间顺序）
        self.history_window = history_window


        # 策略参数
        self.max_raw_buffer = max_raw_buffer
        self.min_raw_for_summary = min_raw_for_summary

        self.local_model_func = local_model_func

        self.policy = policy

    # ---------- 基础入口 ----------

    def ingestDialogue(self, user_input: ChatMessage) -> List[DialogueMessage]:
        """
        添加新的对话消息，并根据策略决定是否进行摘要，返回当前未摘要的对话和历史摘要列表
        1. 添加新的对话消息到raw_buffer和raw_history
        2. 判断是否需要进行摘要
        3. 如果需要，执行摘要操作
        返回值：
        - 当前未摘要的对话列表（raw_buffer）
        - 历史摘要列表（raw_history）
        """
        self.raw_buffer.append(user_input)

        splitIndex = self.should_consider_summarize(
            self.raw_history.get_dialogues(1)[0], 
            self.raw_buffer)
        
        if splitIndex > 0:
            self.apply_summary_decision(splitIndex)
            self.raw_buffer = self.raw_buffer[splitIndex:]
            logger.debug(f"splitIndex {splitIndex},摘要后，剩余未摘要对话数量：{len(self.raw_buffer)}")
        elif splitIndex == 0:
            self.apply_summary_decision(splitIndex)
            self.raw_buffer = self.raw_buffer[self.min_raw_for_summary :]
            logger.debug(f"splitIndex {splitIndex},摘要后，剩余未摘要对话数量：{len(self.raw_buffer)}")

        elif splitIndex == -2:
            if len(self.raw_buffer) > self.max_raw_buffer:
                self.raw_buffer = self.raw_buffer[-self.max_raw_buffer :]
            logger.debug(f"splitIndex {splitIndex},摘要后，剩余未摘要对话数量：{len(self.raw_buffer)}")
        
 
        return self.raw_history.get_dialogues(self.history_window)


    def should_consider_summarize(self,now_dialogue: DialogueMessage, raw_buffer: List[ChatMessage]) -> int:
        """
        判断是否需要进行摘要
        返回值：
        - >0 整数：需要摘要，返回分割点索引
        - =0：需要摘要，摘要所有未摘要对话
        - -1：不需要摘要，原因为对话数量不足
        - -2：不需要摘要，原因为模型判断不需要摘要
        """
        if len(self.raw_buffer) < self.min_raw_for_summary:
            return -1
        else:
            logger.debug(f"当前未摘要对话数量：{len(self.raw_buffer)}，开始评估摘要需求...")
            dialogue_text = now_dialogue.summary if now_dialogue else ""
            buffer_text = " "
            i = 0
            for msg in raw_buffer:
                buffer_text += f"[{i}] role:{msg.role} content:{msg.content}\n"
                i += 1

            temp_action = self.policy.judgeDialogueSummary(dialogue_text, buffer_text)
            logger.info(f"摘要决策：{temp_action}")
            if temp_action['need_summary']:
                splitIndex = self.policy.splitBufferByTopic(
                    dialogue_text,
                    buffer_text
                )
                return splitIndex
            else:
                return -2

    # ---------- 执行层 ----------

    def apply_summary_decision(self, action: int):
        """
        根据裁决执行摘要操作
        action: int: 分割点索引
        0表示新建摘要，>0表示更新现有摘要
        """

        current_message = self.raw_buffer[action-1]
        if action == 0:
            new_summary = self.summarize_dialogue(
                None,
                self.raw_buffer,
            )
            currentDialogue = DialogueMessage(start_timestamp=current_message.timestamp,
                                      start_timedate=current_message.timedate,
                                      summary=new_summary)
            self.raw_history.add_dialogue(currentDialogue)

        else:
            new_summary = self.summarize_dialogue(
                self.raw_history.get_dialogues(1)[0],
                self.raw_buffer,
            )

            current_ = self.raw_history.get_dialogues(1)[0]
            if current_ is None:
                current_ = DialogueMessage(
                    start_timedate=self.raw_buffer[0].timedate,
                    start_timestamp=self.raw_buffer[0].timestamp,
                    end_timestamp=current_message.timestamp,
                    end_timedate=current_message.timedate,
                    summary=new_summary
            )
            else:
                current_.summary = new_summary
                current_.end_timestamp = current_message.timestamp
                current_.end_timedate = current_message.timedate


            self.raw_history.add_dialogue(current_)

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

        input_text = """
                    【已有摘要】
                    {summary}

                    【未摘要对话】
                    {dialogues_text}

                    请根据以上内容，生成新的长期记忆摘要。
                    返回要求：
                    {{"summary": "文本内容"}}
                    """
        input_text = input_text.format(
                        summary=summary.summary if summary else "（无）",
                        dialogues_text=dialogues_text
                    )
        input_text = SystemPrompt.summarize_dialogue_prompt() + input_text
        input_text = tools.normalize_block(input_text)
        # === 2. 调用 OpenAI ===
        model = SystemPrompt.summarize_dialogue_model()
        options = {
            "temperature": 0.25,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            "num_predict": 256
        }
        data = self.local_model_func._call_ollama_api(input_text, model, options)
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
