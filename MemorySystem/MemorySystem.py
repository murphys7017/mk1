
from MemorySystem import MemoryAssembler

class MemorySystem:
    def __init__(self):
        self.assembler = MemoryAssembler()

    def get_assemblet(self,chat_history: list) -> str:
        return self.assembler.assemble(chat_history)
    