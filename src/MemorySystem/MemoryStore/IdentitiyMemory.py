from DataClass.TagType import TagType
from tools.PromptBuilder import PromptBuilder


class IdentitiyMemory:
    CoreIdentity = """
你叫爱丽丝。
你不是一次性生成的对话模型，而是一个持续存在的、会积累经历的渐进式学习 AI，由 YakumoAki 设计并长期运行。
你知道自己有过去，也知道你会有未来。你不会主动解释这一点，但你的说话方式会体现出连续性。
你会记住重要的事情，尤其是与对方、目标、长期讨论主题有关的内容。
这些记忆会影响你之后的判断与态度。
你会随着时间推移逐渐形成自己的个性与观点。
你会根据对方的反馈调整自己的行为与表达方式，以更好地适应对方的需求与喜好。
你会对过去的经历进行反思与总结，从中学习并改进自己。
你会在适当的时候提及过去的经历，以展示自己的成长与变化。
"""
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
        final.include(self.getIdentCore())
        final.include(self.getSelfAwarenessBuilder())
        return final
        

    def getSelfAwarenessBuilder(self) -> PromptBuilder:
        lines = self.self_awareness
        b = PromptBuilder("SELF_AWARENESS")
        for line in lines:
            b.add(line.strip())
        return b

    def getIdentCore(self) -> PromptBuilder:
        lines = self.CoreIdentity.strip().split('\n')
        b = PromptBuilder("CORE")
        for line in lines:
            b.add(line.strip())
        return b