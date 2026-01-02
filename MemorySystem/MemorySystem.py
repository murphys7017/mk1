
from MemorySystem.MemoryAssembler import MemoryAssembler
from MemorySystem.MemoryStore.MemoryStorage import MemoryStorage
from MessageModel import ChatMessage
from RawChatHistory import RawChatHistory

class MemorySystem:
    def __init__(self, raw_history: RawChatHistory):
        self.raw_history = raw_history
        self.strorage = MemoryStorage(raw_history)
        self.assembler = MemoryAssembler(self.strorage)
        


    def buildMessages(self,user_input: ChatMessage) -> str:
        return self.assembler.assemble(user_input)
    