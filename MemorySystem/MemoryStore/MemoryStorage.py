
from LLM.LLMManagement import LLMManagement
from MemorySystem import MemoryPolicy
from RawChatHistory.RawChatHistory import RawChatHistory
from MemorySystem.MemoryStore.DialogueStorage import DialogueStorage
from MemorySystem.MemoryStore.IdentitiyMemory import IdentitiyMemory
from MemorySystem.MemoryPolicy import MemoryPolicy
from DataClass.ChatMessage import ChatMessage
from DataClass.ChatState import ChatState
from DataClass.DialogueMessage import DialogueMessage


class MemoryStorage:
    def __init__(self,raw_history: RawChatHistory, llm_management: LLMManagement, policy: MemoryPolicy):
        self.raw_history = raw_history
        self.identity_memory = IdentitiyMemory()
        self.dialogue_storage = DialogueStorage(raw_history, llm_management, policy)
        

    def getIdentity(self) -> str:
        return self.identity_memory.getIdentity()
    
    def getDialogue(self, user_input: ChatMessage) -> list[DialogueMessage]:
        return self.dialogue_storage.ingestDialogue(user_input)
    
