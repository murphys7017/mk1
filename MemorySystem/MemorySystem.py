
from LLM.LLMManagement import LLMManagement
from MemorySystem.MemoryPolicy import MemoryPolicy
from MemorySystem.MemoryAssembler import MemoryAssembler
from MemorySystem.MemoryStore.MemoryStorage import MemoryStorage
from MessageModel import ChatMessage
from RawChatHistory.RawChatHistory import RawChatHistory

class MemorySystem:
    def __init__(self, raw_history: RawChatHistory, llm_management: LLMManagement):
        self.raw_history = raw_history
        self.llm_management = llm_management

        self.memory_policy = MemoryPolicy(llm_management)
        self.strorage = MemoryStorage(raw_history, self.llm_management,self.memory_policy)
        self.assembler = MemoryAssembler(self.strorage, raw_history)
        

    def assemble(self) -> str:
        return self.assembler.assemble()