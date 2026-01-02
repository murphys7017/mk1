
from MemorySystem.MemoryStore.DialogueStorage import DialogueStorage
from MemorySystem.MemoryStore.IdentitiyMemory import IdentitiyMemory


class MemoryStorage:
    def __init__(self):
        self.identity_memory = IdentitiyMemory()
        self.dialogue_storage = DialogueStorage()

    def getIdentity(self) -> str:
        return self.identity_memory.getIdentity()
    
    def getDialogue(self, chat_history: list) -> list:
        return self.dialogue_storage.dialogues

class MemoryAssembler:
    def __init__(self):
        self.strorage = MemoryStorage()

    def assemble(self, chat_history: list) -> str:
        messages = []
        identity_prompt = self.strorage.getIdentity()
        chat_history_prompt = self.strorage.getDialogue(chat_history)
        chat_history = chat_history[-10:]
        return self.strorage.getIdentity()