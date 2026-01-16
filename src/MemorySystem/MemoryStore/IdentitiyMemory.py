from DataClass.TagType import TagType
from tools.PromptBuilder import PromptBuilder


class IdentitiyMemory:
    def __init__(self):
        self.loadSelfAwareness()
        pass
    def updateSelfAwareness(self, new_awareness: str):
        pass
    def loadSelfAwareness(self):
        with open('Alice_personality.txt', 'r', encoding='utf-8') as f:
            self.self_awareness = f.readlines()

    def getSelfAwareness(self) -> str:
        return ''.join(self.self_awareness)
    
    def getIdentity(self) -> PromptBuilder:
        final = PromptBuilder(TagType.IDENTITY_CORE_TAG)
        final.include(self.getSelfAwarenessBuilder())
        return final
        

    def getSelfAwarenessBuilder(self) -> PromptBuilder:
        lines = self.self_awareness
        b = PromptBuilder("SELF_AWARENESS")
        for line in lines:
            b.add(line.strip())
        return b
