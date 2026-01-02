
from MemorySystem.MemoryStore.MemoryStorage import MemoryStorage


class MemoryAssembler:
    def __init__(self):
        self.strorage = MemoryStorage()

    def assemble(self, chat_history: list) -> str:
        messages = []
        identity_prompt = self.strorage.getIdentity()
        chat_history_prompt = self.strorage.getDialogue(chat_history)
        chat_history = chat_history[-10:]
        return self.strorage.getIdentity()