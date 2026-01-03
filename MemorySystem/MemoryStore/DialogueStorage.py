import time
from typing import List, Optional, Literal
import time
from dataclasses import dataclass
import json

from LocalModelFunc import LocalModelFunc
from RawChatHistory import RawChatHistory
from MessageModel import ChatMessage, DialogueMessage


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
        max_raw_buffer: int = 10,
        min_raw_for_summary: int = 10,
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

        self.local_model_func = LocalModelFunc()

    # ---------- 基础入口 ----------

    def ingestDialogue(self, user_input: ChatMessage):
        """
        添加新的对话消息，并根据策略决定是否进行摘要，返回当前未摘要的对话和历史摘要列表
        1. 添加新的对话消息到raw_buffer和raw_history
        2. 判断是否需要进行摘要
        3. 如果需要，执行摘要操作
        返回值：
        - 当前未摘要的对话列表（raw_buffer）
        - 历史摘要列表（raw_history）
        """
        self.raw_history.add_message(user_input)
        self.raw_buffer.append(user_input)

        splitIndex = self.should_consider_summarize(
            self.raw_history.get_dialogues(1)[0], 
            self.raw_buffer)
        
        if splitIndex >= 0:
            self.apply_summary_decision(splitIndex)
            self.raw_buffer = self.raw_buffer[splitIndex-1 :]

        elif splitIndex == -2:
            if len(self.raw_buffer) > self.max_raw_buffer:
                self.raw_buffer = self.raw_buffer[-self.max_raw_buffer :]
        
 
        return self.raw_buffer,self.raw_history.get_dialogues(self.history_window)


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
            dialogue_text = now_dialogue.summary if now_dialogue else ""
            buffer_text = " "
            i = 1
            for msg in raw_buffer:
                buffer_text += f"[{i}] role:{msg.role} content:{msg.content}\n"
                i += 1

            temp_action = self.local_model_func.judge_dialogue_summary(dialogue_text, buffer_text)
            

            if temp_action['need_summary']:
                splitIndex = self.local_model_func.split_buffer_by_topic_continuation(
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
            new_summary = self.local_model_func.summarize_dialogue(
                None,
                self.raw_buffer,
            )
            currentDialogue = DialogueMessage(start_timestamp=current_message.start_timestamp,
                                      start_timedate=current_message.start_timedate,
                                      summary=new_summary)
            self.raw_history.add_dialogue(currentDialogue)

        else:
            new_summary = self.local_model_func.summarize_dialogue(
                self.raw_history.get_dialogues(1)[0],
                self.raw_buffer,
            )

            current_ = self.raw_history.get_dialogues(1)[0]
            current_.summary = new_summary
            current_.end_timestamp = current_message.start_timestamp
            current_.end_timedate = current_message.start_timedate


            self.raw_history.add_dialogue(current_)

