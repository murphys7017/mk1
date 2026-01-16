import asyncio
from loguru import logger

from ChatStateSystem.ChatStateSystem import ChatStateSystem
from DataClass.ChatEvent import ChatEvent
from DataClass.ChatMessage import ChatMessage
from DataClass.EventType import EventType
from MemorySystem.MemorySystem import MemorySystem
from PostTreatmentSystem.PostHandleSystem import PostHandleSystem
from RawChatHistory.RawChatHistory import RawChatHistory


class PostTurnProcessor:
    """
    Post-turn pipeline that reacts to events and dispatches follow-up modules.
    """

    def __init__(
        self,
        event_bus,
        memory_system: MemorySystem,
        chat_state_system: ChatStateSystem,
        raw_history: RawChatHistory,
        post_handle_system: PostHandleSystem
    ):
        self.event_bus = event_bus
        self.memory_system = memory_system
        self.chat_state_system = chat_state_system
        
        self.raw_history = raw_history
        self.post_handle_system = post_handle_system

        self._last_processed_turn_id: int | None = None

        # 单入口：统一在这里处理“回合完成”事件
        self.event_bus.subscribe(
            EventType.ASSISTANT_RESPONSE_GENERATED,
            self._handle_assistant_response
        )
        self.event_bus.subscribe(
            EventType.POST_HANDLE_COMPLETED,
            self._handle_post_handle_completed
        )
    def _handle_post_handle_completed(self, event: ChatEvent):
        if not self._should_process(event):
            return


    async def _handle_assistant_response(self, event: ChatEvent):
        if not self._should_process(event):
            return

        # 统一调度：摘要/状态更新/未来的长期记忆
        try:
            if self.memory_system.storage.dialogue_storage:
                # may be IO-bound but synchronous here
                self.memory_system.storage.maybeUpdateDialogueSummary()

            if self.chat_state_system:
                self.chat_state_system.checkAndUpdateState(event.turn_id)

            # TODO:这个是AI自己瞎写的吗？
            # if self.memory_long:
            #     handler = getattr(self.memory_long, "process_event", None)
            #     if callable(handler):
            #         # allow sync handler
            #         handler(event)

            if self.post_handle_system:
                # schedule post_handle_system.handle asynchronously
                try:
                    asyncio.create_task(self.post_handle_system.handle(timeout=20.0))
                except Exception as exc:
                    logger.warning(f"PostTurnProcessor failed to invoke PostHandleSystem: {exc}")
        except Exception as exc:
            logger.exception(f"_handle_assistant_response internal error: {exc}")
        

    def _should_process(self, event: ChatEvent) -> bool:
        # 若有 turn_id，按回合去重
        if event.turn_id is None or event.turn_id <= 0:
            return True

        if self._last_processed_turn_id is None or event.turn_id > self._last_processed_turn_id:
            self._last_processed_turn_id = event.turn_id
            return True

        return False

    def _extract_messages(self, event: ChatEvent) -> list[ChatMessage]:
        # 兼容常见 payload 结构，不满足则回退到最近历史
        data = event.data
        if isinstance(data, ChatMessage):
            return [data]

        if isinstance(data, list) and all(isinstance(item, ChatMessage) for item in data):
            return data

        if isinstance(data, dict):
            candidate = data.get("messages") or data.get("message")
            if isinstance(candidate, ChatMessage):
                return [candidate]
            if isinstance(candidate, list) and all(isinstance(item, ChatMessage) for item in candidate):
                return candidate

        if self.raw_history:
            try:
                return self.raw_history.getHistory(2)
            except Exception as exc:
                logger.warning(f"Failed to read history for post turn: {exc}")

        return []
