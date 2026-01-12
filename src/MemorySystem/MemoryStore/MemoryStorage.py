
from LLM.LLMManagement import LLMManagement
from MemorySystem import MemoryPolicy
from RawChatHistory.RawChatHistory import RawChatHistory
from MemorySystem.MemoryStore.DialogueStorage import DialogueStorage
from MemorySystem.MemoryStore.IdentitiyMemory import IdentitiyMemory
from MemorySystem.MemoryPolicy import MemoryPolicy
from DataClass.DialogueMessage import DialogueMessage
from tools.PromptBuilder import PromptBuilder


class MemoryStorage:
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
        

    def getIdentity(self) -> PromptBuilder:
        return self.identity_memory.getIdentity()
    
    def getDialogue(self) -> list[DialogueMessage]:
        return self.dialogue_storage.ingestDialogue()
    
