
from LocalModelFunc import LocalModelFunc
from MemorySystem import MemoryPolicy
from MemorySystem.MemoryStore.ChatStateStorage import ChatStateStorage
from RawChatHistory.RawChatHistory import RawChatHistory
from MemorySystem.MemoryStore.DialogueStorage import DialogueStorage
from MemorySystem.MemoryStore.IdentitiyMemory import IdentitiyMemory
from MemorySystem.MemoryPolicy import MemoryPolicy
from MessageModel import ChatMessage, ChatState, DialogueMessage


class MemoryStorage:
    def __init__(self,raw_history: RawChatHistory, local_model_func: LocalModelFunc, policy: MemoryPolicy):
        self.raw_history = raw_history
        self.identity_memory = IdentitiyMemory()
        self.dialogue_storage = DialogueStorage(raw_history, local_model_func, policy)
        self.chat_state_storage = ChatStateStorage(raw_history, local_model_func)
        

    def getIdentity(self) -> str:
        return self.identity_memory.getIdentity()
    
    def getDialogue(self, user_input: ChatMessage) -> list[DialogueMessage]:
        return self.dialogue_storage.ingestDialogue(user_input)
    

    def getChatState(self) -> ChatState:
        return self.chat_state_storage.getChatState()
    def checkAndUpdateState(self):
        self.chat_state_storage.checkAndUpdateState()
        return self.chat_state_storage.getChatState()