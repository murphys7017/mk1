from typing import List

from loguru import logger

from DataClass.DialogueDecision import DecisionType, SummaryDecision
from LLM.LLMManagement import LLMManagement
from RawChatHistory.RawChatHistory import RawChatHistory
from DataClass.ChatMessage import ChatMessage
from DataClass.DialogueMessage import DialogueMessage
from MemorySystem.MemoryPolicy import MemoryPolicy


class DialogueStorage:
    """
    管理：
    - 已摘要消息
    - 未摘要消息
    - 近期摘要
    """

    def __init__(
        self,
        # 近期消息窗口（消息轮数）
        history_window: int,
        # 近期摘要窗口（摘要条数）
        summary_window: int,
        raw_history: RawChatHistory,
        llm_management: LLMManagement,
        policy: MemoryPolicy,
        # 达到该数量后检查是否需要摘要
        min_raw_for_summary: int = 4,


    ):
        self.raw_history = raw_history
        self.llm_management = llm_management
        self.policy = policy

        self.max_raw_buffer = history_window
        self.min_raw_for_summary = min_raw_for_summary
        self.history_window = history_window
        self.summary_window = summary_window

        # 已摘要/未摘要消息
        self.summarized_messages: List[ChatMessage] = []
        self.unsummarized_messages: List[ChatMessage] = []
        self.recent_summaries: List[DialogueMessage] = []

    # ---------- 基础入口 ----------
    def maybeUpdateDialogueSummary(self) -> None:
        """
        检查并更新对话摘要。
        返回值：更新后的近期摘要列表
        """
        # Avoid running multiple concurrent ingest jobs
        if getattr(self, "_ingest_in_progress", False):
            logger.debug("ingestDialogue already in progress, skipping")
            return

        def _done_callback(fut=None):
            try:
                # clear flag regardless of success
                self._ingest_in_progress = False
            except Exception:
                logger.exception("Error clearing ingest in-progress flag")

        # Wrapper that will call the blocking ingestDialogue and handle exceptions
        def _run_blocking_ingest():
            try:
                self.ingestDialogue()
            except Exception:
                logger.exception("Background ingestDialogue failed")
            finally:
                # Ensure flag cleared
                try:
                    self._ingest_in_progress = False
                except Exception:
                    logger.exception("Error clearing ingest in-progress flag in thread")

        # Try to schedule on the running asyncio loop without blocking it
        try:
            import asyncio

            loop = asyncio.get_running_loop()
            # mark as in progress
            self._ingest_in_progress = True

            async def _async_wrapper():
                try:
                    await loop.run_in_executor(None, self.ingestDialogue)
                except Exception:
                    logger.exception("Background ingestDialogue (async) failed")
                finally:
                    self._ingest_in_progress = False

            # create task but don't await it
            loop.create_task(_async_wrapper())
            return
        except RuntimeError:
            # No running event loop in this thread; fallback to a daemon thread
            import threading

            self._ingest_in_progress = True
            t = threading.Thread(target=_run_blocking_ingest, daemon=True)
            t.start()
            return

    def ingestDialogue(self) -> List[DialogueMessage]:
        self._refresh_buffers()

        decision = self.should_consider_summarize(
            self.summarized_messages,
            self.unsummarized_messages,
            self.recent_summaries,
        )

        logger.info(
            f"[DialogueStorage] decision={decision.type} action={decision.summary_action} "
            f"split_index={decision.split_index} reason={decision.reason}"
        )

        if decision.type is DecisionType.SUMMARIZE and self.unsummarized_messages:
            split_index = decision.split_index
            if split_index is None:
                logger.error("split_index is None for SUMMARIZE decision, skipping summarization")
                return self.recent_summaries

            max_index = len(self.unsummarized_messages) - 1
            if split_index > max_index:
                logger.error(f"split_index out of range: {split_index} > {max_index}")
                logger.warning(f"调整 split_index：{split_index} -> {max_index}")
                split_index = max_index

            min_index = min(self.min_raw_for_summary - 1, max_index)
            split_index = max(split_index, min_index)

            self.apply_summary_decision(split_index)
            self._refresh_buffers()

        return self.recent_summaries


    def should_consider_summarize(
        self,
        summarized_messages: List[ChatMessage],
        unsummarized_messages: List[ChatMessage],
        recent_summaries: List[DialogueMessage],
    ) -> SummaryDecision:
        if len(unsummarized_messages) < self.min_raw_for_summary:
            return SummaryDecision(
                type=DecisionType.WAIT,
                reason=f"unsummarized<{self.min_raw_for_summary}",
                summary_action=None,
            )

        summary_text = self._build_summary_text(recent_summaries)
        buffer_text = self._build_dialogue_text(
            summarized_messages, unsummarized_messages, include_summarized=True
        )

        judge = self.policy.judgeDialogueSummary(summary_text, buffer_text)
        need = bool(judge.get("need_summary", False))
        action = (judge.get("summary_action") or "none").strip()

        if (not need) or action == "none":
            return SummaryDecision(
                type=DecisionType.SKIP,
                reason=f"judge need_summary={need}, summary_action={action}",
                summary_action="none",
            )

        # action == "new"：无需 split，直接尽快生成新摘要（覆盖到末尾）
        if action == "new":
            return SummaryDecision(
                type=DecisionType.SUMMARIZE,
                reason="judge summary_action=new",
                summary_action="new",
                split_index=len(unsummarized_messages) - 1,
            )

        # action == "merge"：A 方案：splitBufferByTopic 返回 continuation_turns（数量）
        x = self.policy.splitBufferByTopic(
            current_summary=summary_text,
            dialogue_turns=buffer_text,
        )

        if x <= 0:
            # merge 但没有延续：降级为 new（更符合直觉：新话题开了）
            return SummaryDecision(
                type=DecisionType.SUMMARIZE,
                reason="merge requested but continuation_turns=0 -> degrade to new",
                summary_action="new",
                split_index=len(unsummarized_messages) - 1,
            )

        # count -> index
        split_index = x - 1
        return SummaryDecision(
            type=DecisionType.SUMMARIZE,
            reason=f"merge continuation_turns={x}",
            summary_action="merge",
            split_index=split_index,
        )

    
    def should_consider_summarize_bk(
        self,
        summarized_messages: List[ChatMessage],
        unsummarized_messages: List[ChatMessage],
        recent_summaries: List[DialogueMessage],
    ) -> int:
        """
        判断是否需要进行摘要。
        返回值：
        - >0 整数：需要摘要，返回分割点索引
        - =0：需要摘要
        - -1：对话数量不足
        - -2：模型判定不需要摘要
        """
        if len(unsummarized_messages) < self.min_raw_for_summary:
            return -1

        logger.debug(f"当前未摘要消息数量：{len(unsummarized_messages)}，开始评估是否摘要")
        summary_text = self._build_summary_text(recent_summaries)
        buffer_text = self._build_dialogue_text(summarized_messages, unsummarized_messages, include_summarized=True)

        temp_action = self.policy.judgeDialogueSummary(summary_text, buffer_text)
        logger.info(f"摘要决策：{temp_action}")
        if temp_action.get("need_summary"):
            split_index = self.policy.splitBufferByTopic(
                summary_text,
                buffer_text
            )
            if split_index <= 0:
                return -1
            return split_index - 1

        return -2

    # ---------- 执行层 ----------

    def apply_summary_decision(self, action: int):
        """
        根据裁决执行摘要操作
        action: int: 分割点索引
        """
        current_message = self.unsummarized_messages[action]
        summary_res = self.summarize_dialogue(
            self.recent_summaries,
            self.unsummarized_messages[: action + 1],
            self.summarized_messages,
        )
        

        logger.info(f"生成摘要结果：{summary_res}")
        if summary_res["action"] == "new":
            start_turn_id = self.unsummarized_messages[0].chat_turn_id
            current_dialogue = DialogueMessage(
                start_turn_id=start_turn_id if start_turn_id is not None else -1,
                end_turn_id=current_message.chat_turn_id,
                dialogue_turns=action + 1,
                is_completed=False,
                summary=summary_res["summary_content"],
            )
            self.raw_history.addDialogues(current_dialogue)
        elif summary_res["action"] == "update":
            if summary_res["summary_id"] == -1:
                logger.warning("摘要模型未返回有效摘要ID，跳过摘要操作")
                return
        
            dialogue = summary_res["dialogue"]
            dialogue.summary = summary_res["summary_content"]
            dialogue.end_turn_id = current_message.chat_turn_id
            dialogue.dialogue_turns = action + 1
            self.raw_history.updateDialogue(dialogue)
        

    def summarize_dialogue(
        self,
        summaries: list[DialogueMessage],
        dialogues: list[ChatMessage],
        summarized_messages: list[ChatMessage],
    ) -> dict:
        """
        使用摘要模型生成面向长期记忆的摘要文本。
        """
        summary_text = self._build_summary_text(summaries)
        dialogues_text = self._build_dialogue_text(summarized_messages, dialogues, include_summarized=True)

        options = {
            "temperature": 0.25,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            "num_predict": 256
        }
        data = self.llm_management.generate(
            prompt_name="summarize_dialogue",
            options=options,
            summary_text=summary_text,
            dialogues_text=dialogues_text
        )

        dialogue_id = data.get("summary_id", None)
        try:
            dialogue_id = int(dialogue_id) if dialogue_id is not None else None
        except (TypeError, ValueError):
            dialogue_id = None

        if dialogue_id:
            dialogue = self.raw_history.getDialogueById(dialogue_id)
            if dialogue is not None:
                summary_text = (data.get("summary_content", "（无）")).strip()
                summary_action = (data.get("action", "update")).strip()

                summary_text = summary_text.strip()
                if len(summary_text) < 5:
                    summary_text = "（无）"

                return {
                    "summary_id": dialogue_id,
                    "summary_content": summary_text,
                    "action": summary_action,
                    "dialogue": dialogue
                }

        return {
            "summary_id": -1,
            "summary_content": "（无）",
            "action": "new"
        }

    # ---------- 内部工具 ----------

    def _refresh_buffers(self) -> DialogueMessage | None:
        self.recent_summaries = self.raw_history.getDialogues(self.summary_window)
        recent_messages = self.raw_history.getHistory(self.history_window)

        last_summary = self.recent_summaries[-1] if self.recent_summaries else None
        last_summary_end = None
        if last_summary:
            if last_summary.end_turn_id is not None:
                last_summary_end = last_summary.end_turn_id
            elif last_summary.start_turn_id is not None:
                last_summary_end = last_summary.start_turn_id

        self.summarized_messages = []
        self.unsummarized_messages = []
        for msg in recent_messages:
            if last_summary_end is None:
                self.unsummarized_messages.append(msg)
            else:
                if msg.chat_turn_id is not None and msg.chat_turn_id <= last_summary_end:
                    self.summarized_messages.append(msg)
                else:
                    self.unsummarized_messages.append(msg)

        if len(self.unsummarized_messages) > self.max_raw_buffer:
            self.unsummarized_messages = self.unsummarized_messages[-self.max_raw_buffer :]

        return last_summary

    def _build_summary_text(self, summaries: list[DialogueMessage]) -> str:
        summary_text = ""
        if summaries:
            for summary in summaries:
                summary_text += f"- [summary_id]{summary.dialogue_id}[summary_content]{summary.summary}\n"
        return summary_text

    def _build_message_block(self, messages: list[ChatMessage]) -> str:
        buffer_text = ""
        for i, msg in enumerate(messages):
            buffer_text += f"[{i}] role:{msg.role} content:{msg.content}\n"
        return buffer_text

    def _build_dialogue_text(
        self,
        summarized_messages: list[ChatMessage],
        unsummarized_messages: list[ChatMessage],
        include_summarized: bool,
    ) -> str:
        parts = []
        if include_summarized and summarized_messages:
            parts.append("【已摘要消息】")
            parts.append(self._build_message_block(summarized_messages))

        parts.append("【未摘要消息】")
        parts.append(self._build_message_block(unsummarized_messages))
        return "\n".join(parts).strip()

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
