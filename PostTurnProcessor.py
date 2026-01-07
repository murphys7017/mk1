from loguru import logger

from ChatStateSystem.ChatStateSystem import ChatStateSystem
from DataClass.ChatEvent import ChatEvent
from DataClass.ChatMessage import ChatMessage
from DataClass.EventType import EventType
from MemorySystem.MemorySystem import MemorySystem
from RawChatHistory.RawChatHistory import RawChatHistory


class PostTurnProcessor:
    """
    Post-turn pipeline that reacts to events and dispatches follow-up modules.
    """

    def __init__(
        self,
        memory_long,
        event_bus,
        memory_system: MemorySystem,
        chat_state_system: ChatStateSystem,
        raw_history: RawChatHistory,
    ):
        self.event_bus = event_bus
        self.memory_system = memory_system
        self.chat_state_system = chat_state_system

        self.memory_long = memory_long
        
        self.raw_history = raw_history

        self._last_processed_turn_id: int | None = None

        # 单入口：统一在这里处理“回合完成”事件
        self.event_bus.subscribe(
            EventType.ASSISTANT_RESPONSE_GENERATED,
            self._handle_assistant_response
        )

    def _handle_assistant_response(self, event: ChatEvent):
        if not self._should_process(event):
            return

        # 统一调度：摘要/状态更新/未来的长期记忆
        if self.memory_system.strorage.dialogue_storage:
            self.memory_system.strorage.getDialogue()

        if self.chat_state_system:
            self.chat_state_system.checkAndUpdateState()

        if self.memory_long:
            handler = getattr(self.memory_long, "process_event", None)
            if callable(handler):
                handler(event)

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
