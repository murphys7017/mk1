
from MemorySystem.MemoryStore.MemoryStorage import MemoryStorage
from DataClass.ChatMessage import ChatMessage
from loguru import logger
from tools import tools
from RawChatHistory.RawChatHistory import RawChatHistory
from DataClass.TagType import TagType

class MemoryAssembler:
    def __init__(self,
                 strorage: MemoryStorage,
                 raw_history: RawChatHistory,
                 history_window: int = 20,
                 ):
        self.history_window = history_window
        self.strorage = strorage
        self.raw_history = raw_history



    def _build_identity_core(self) -> str:
        return f"""
        <{TagType.IDENTITY_CORE_TAG}>
        {self.strorage.getIdentity()}
        </{TagType.IDENTITY_CORE_TAG}>
        """.strip()
    
    def _build_world_setting(self) -> str:
        return f"""
        <{TagType.WORLD_SETTING_TAG}>
        （当前暂无世界设定）
        </{TagType.WORLD_SETTING_TAG}>
        """.strip()
    
    def _build_long_memory(self) -> str:
        return f"""
        <{TagType.IMEMORY_LONG_TAG}>
        （当前暂无长期记忆）
        </{TagType.IMEMORY_LONG_TAG}>
        """.strip()
    def _build_knowledge(self) -> str:
        return f"""
        <{TagType.KNOWLEDGE_TAG}>
        （当前暂无知识库内容）
        </{TagType.KNOWLEDGE_TAG}>
        """.strip()
    
    def _build_mid_memory(self) -> str:
        dialogues = self.raw_history.getDialogues(3)
        summary = ""
        i= 1
        for msg in dialogues:
            if msg is None:
                break
            summary += f"[{i}] {msg.summary}\n"
            i += 1

        return f"""
        <{TagType.MEMORY_MID_TAG}>
        {summary if summary != "" else "（无）"}
        </{TagType.MEMORY_MID_TAG}>
        """.strip()

    
    def assemble(self) -> str:

        messages = []

        system_prompt = f"""
        {self._build_identity_core()}
        {self._build_world_setting()}
        {self._build_long_memory()}
        {self._build_knowledge()}
        {self._build_mid_memory()}
        """
        # messages.append({
        #     "role": "system",
        #     "content": tools.normalizeBlock(system_prompt)
        # })

        # # 原始对话放最后
        # buffer = self.raw_history.getHistory(self.history_window)
        # for msg in buffer:
        #     messages.append(msg.buildMessage())
        
        return system_prompt
