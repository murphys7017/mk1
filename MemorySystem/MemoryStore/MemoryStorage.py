
from RawChatHistory import RawChatHistory
from MemorySystem.MemoryStore.DialogueStorage import DialogueStorage
from MemorySystem.MemoryStore.IdentitiyMemory import IdentitiyMemory
from MessageModel import ChatMessage


class MemoryStorage:
    def __init__(self,raw_history: RawChatHistory):
        self.raw_history = raw_history
        self.identity_memory = IdentitiyMemory()
        self.dialogue_storage = DialogueStorage(raw_history)
        

    def getIdentity(self) -> str:
        return self.identity_memory.getIdentity()
    
    def getDialogue(self, user_input: ChatMessage) -> list:
        return self.dialogue_storage.ingestDialogue(user_input)