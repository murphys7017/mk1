from DataClass.TagType import TagType
from tools.PromptBuilder import PromptBuilder


class WordCoreStorage:
    Core= """
你叫爱丽丝。
你是一个长期运行的、本地部署的智能体系统，而不是一次性生成的对话模型。
对话是有上下文连续性的，你应优先利用当前会话中明确提供的信息。
如果相关记忆或信息未被提供，你必须明确说明不知道，而不是假设自己记得。
"""
    def __init__(self):
        pass

        


    def getWorldCore(self) -> PromptBuilder:
        lines = self.Core.strip().split('\n')
        b = PromptBuilder(TagType.WORLD_CORE_TAG)
        for line in lines:
            b.add(line.strip())
        return b