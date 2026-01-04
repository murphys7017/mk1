
from LocalModelFunc import LocalModelFunc
from MemorySystem.MemoryPolicy import MemoryPolicy
from MemorySystem.MemoryAssembler import MemoryAssembler
from MemorySystem.MemoryStore.MemoryStorage import MemoryStorage
from MessageModel import ChatMessage
from RawChatHistory import RawChatHistory

class MemorySystem:
    def __init__(self, raw_history: RawChatHistory, local_model_func: LocalModelFunc):
        self.raw_history = raw_history
        self.local_model_func = local_model_func

        self.memory_policy = MemoryPolicy(local_model_func)
        self.strorage = MemoryStorage(raw_history, self.local_model_func,self.memory_policy)
        self.assembler = MemoryAssembler(self.strorage, raw_history)
        

    def buildMessages(self,user_input: ChatMessage) -> list[dict]:
        return self.assembler.assemble(user_input)
    