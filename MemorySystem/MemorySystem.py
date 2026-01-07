
from LLM.LLMManagement import LLMManagement
from MemorySystem.MemoryPolicy import MemoryPolicy
from MemorySystem.MemoryAssembler import MemoryAssembler
from MemorySystem.MemoryStore.MemoryStorage import MemoryStorage
from DataClass.ChatMessage import ChatMessage
from RawChatHistory.RawChatHistory import RawChatHistory

class MemorySystem:
    def __init__(self, 
                # 近期消息窗口（消息轮数）
                history_window: int,
                # 近期摘要窗口（摘要条数）
                summary_window: int,
                min_raw_for_summary: int,
                raw_history: RawChatHistory, 
                llm_management: LLMManagement
                ):
        self.raw_history = raw_history
        self.llm_management = llm_management

        self.memory_policy = MemoryPolicy(llm_management)

        self.strorage = MemoryStorage(
            history_window, summary_window, min_raw_for_summary,
            raw_history, self.llm_management,self.memory_policy)
        
        self.assembler = MemoryAssembler(self.strorage, raw_history)
        

    def assemble(self) -> str:
        return self.assembler.assemble()