
from MemorySystem.MemoryStore.MemoryStorage import MemoryStorage
from DataClass.ChatMessage import ChatMessage
from loguru import logger
from tools.PromptBuilder import PromptBuilder
from tools.tools import tools
from RawChatHistory.RawChatHistory import RawChatHistory
from DataClass.TagType import TagType

class MemoryAssembler:
    def __init__(self,
                 storage: MemoryStorage,
                 raw_history: RawChatHistory,
                 history_window: int = 20,
                 ):
        self.history_window = history_window
        self.storage = storage
        self.raw_history = raw_history


    def _build_mid_memory(self) -> PromptBuilder:
        dialogues = self.raw_history.getDialogues(3)
        b = PromptBuilder(TagType.MEMORY_MID_TAG)
        i= 1
        for msg in dialogues:
            if msg is None:
                break
            b.add(f"[{i}] {msg.summary}")
            i += 1
        return b

    
    def assemble(self) -> PromptBuilder:
        # Build memory prompt:
        # - identity core (stable persona / facts)
        # - mid memory (recent dialogue summaries)
        system_prompt = PromptBuilder()

        identity = self.storage.getIdentity()

        memory_prompt = PromptBuilder(TagType.MEMORY_SYSTEM_TAG)
        memory_prompt.include(self._build_mid_memory())

        system_prompt.include(identity)
        system_prompt.include(memory_prompt)
        

        return system_prompt