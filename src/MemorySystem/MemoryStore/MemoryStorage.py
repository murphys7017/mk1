
from typing import Any
from LLM.LLMManagement import LLMManagement
from MemorySystem import MemoryPolicy
from MemorySystem.MemoryStore.WordCoreStorage import WordCoreStorage
from RawChatHistory.RawChatHistory import RawChatHistory
from MemorySystem.MemoryStore.DialogueStorage import DialogueStorage
from MemorySystem.MemoryStore.IdentitiyMemory import IdentitiyMemory
from MemorySystem.MemoryPolicy import MemoryPolicy
from DataClass.DialogueMessage import DialogueMessage
from tools.PromptBuilder import PromptBuilder
from MemorySystem.MemoryStore.BaseStore import BaseStore


class MemoryStorage(BaseStore):
    def __init__(self,
                # 近期消息窗口（消息轮数）
                history_window: int,
                # 近期摘要窗口（摘要条数）
                summary_window: int,
                min_raw_for_summary: int,
                raw_history: RawChatHistory, 
                llm_management: LLMManagement, 
                policy: MemoryPolicy):
        
        self.raw_history = raw_history
        self.identity_memory = IdentitiyMemory()
        self.dialogue_storage = DialogueStorage(
            history_window,
            summary_window,
            raw_history, 
            llm_management, 
            policy)
        self.world_core_storage = WordCoreStorage()
        

    def getIdentity(self) -> PromptBuilder:
        return self.identity_memory.getIdentity()
    
    def maybeUpdateDialogueSummary(self) ->None:
        return self.dialogue_storage.maybeUpdateDialogueSummary()
    

    def getWorldCore(self) -> PromptBuilder:
        return self.world_core_storage.getWorldCore()
    
    
    # ---- DB / history wrappers (统一通过 MemoryStorage 访问 RawChatHistory) ----
    
    
    def add_history(self, history) -> int:
        """Add a ChatMessage to history via RawChatHistory and return turn_id."""
        return self.raw_history.addMessage(history)

    def get_history(self, length: int = -1):
        return self.raw_history.getHistory(length)
    def get_history_by_id(self, id: int) -> Any | None:
        return None

    def get_history_by_role(self, role: str, length: int = -1, sender_id: int | None = None):
        return self.raw_history.getHistoryByRole(role, length, sender_id=sender_id)

    def delete_history_by_id(self, chat_turn_id: int):
        return self.raw_history.deleteMessageById(chat_turn_id)

    def update_history(self, obj):
        pass
    