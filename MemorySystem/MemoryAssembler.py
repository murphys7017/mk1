
from MemorySystem.MemoryStore.MemoryStorage import MemoryStorage
from MessageModel import ChatMessage
from loguru import logger
from tools import tools
from RawChatHistory import RawChatHistory

class MemoryAssembler:
    def __init__(self,
                 strorage: MemoryStorage,
                 raw_history: RawChatHistory,
                 history_window: int = 20,
                 ):
        self.history_window = history_window
        self.strorage = strorage
        self.raw_history = raw_history

        self.IDENTITY_CORE_TAG = "IDENTITY_CORE" # 核心身份 + 长期自我（不可违背）
        self.WORLD_SETTING_TAG = "WORLD_SETTING" # 世界设定 / 运行规则
        self.IMEMORY_LONG_TAG = "MEMORY_LONG" # 已摘要的长期记忆
        self.MEMORY_MID_TAG = "MEMORY_MID" # 已摘要的中期记忆
        self.KNOWLEDGE_TAG = "KNOWLEDGE" # 显式知识 / 世界知识
        self.RESPONSE_PROTOCOL_TAG = "RESPONSE_PROTOCOL" # 回答规范
        self.CHAT_STATE_TAG = "CHAT_STATE" # 对话状态



    def _build_identity_core(self) -> str:
        return f"""
        <{self.IDENTITY_CORE_TAG}>
        {self.strorage.getIdentity()}
        </{self.IDENTITY_CORE_TAG}>
        """.strip()
    
    def _build_world_setting(self) -> str:
        return f"""
        <{self.WORLD_SETTING_TAG}>
        （当前暂无世界设定）
        </{self.WORLD_SETTING_TAG}>
        """.strip()
    
    def _build_long_memory(self) -> str:
        return f"""
        <{self.IMEMORY_LONG_TAG}>
        （当前暂无长期记忆）
        </{self.IMEMORY_LONG_TAG}>
        """.strip()
    def _build_knowledge(self) -> str:
        return f"""
        <{self.KNOWLEDGE_TAG}>
        （当前暂无知识库内容）
        </{self.KNOWLEDGE_TAG}>
        """.strip()
    
    def _build_mid_memory(self, user_input: ChatMessage) -> str:
        dialogues = self.strorage.getDialogue(user_input)
        summary = ""
        i= 1
        for msg in dialogues:
            if msg is None:
                break
            summary += f"[{i}] {msg.summary}\n"
            i += 1

        return f"""
        <{self.MEMORY_MID_TAG}>
        {summary if summary != "" else "（无）"}
        </{self.MEMORY_MID_TAG}>
        """.strip()
    
    def _build_chat_state(self) -> str:
        chat_state = self.strorage.getChatState()
        return f"""
        <{self.CHAT_STATE_TAG}>
        - interaction:{chat_state.interaction}
        - user_attitude:{chat_state.user_attitude}
        - emotional_state:{chat_state.emotional_state}
        - leading_approach:{chat_state.leading_approach}
        - last_message_analysis: {self.raw_history.get_history()[-1].getExtra()}
        </{self.CHAT_STATE_TAG}>
        """.strip()
    

    def _build_response_guidelines(self) -> str:
        return f"""
        <{self.RESPONSE_PROTOCOL_TAG}>
        你将接收到一些结构化上下文。
        它们仅用于你理解情况。

        【绝对规则】
        - 你的回复必须是纯自然语言
        - 不得包含任何 XML、标签、结构化内容
        - 不得重复或模仿输入格式
        - 直接像真人一样说话
        </{self.RESPONSE_PROTOCOL_TAG}>
        """.strip()
    
    

    
    def assemble(self, user_input: ChatMessage) -> list[dict]:

        messages = []

        system_prompt = f"""
        {self._build_identity_core()}
        {self._build_world_setting()}
        {self._build_long_memory()}
        {self._build_knowledge()}
        {self._build_mid_memory(user_input)}
        {self._build_chat_state()}
        {self._build_response_guidelines()}
        """
        messages.append({
            "role": "system",
            "content": tools.normalize_block(system_prompt)
        })

        # 原始对话放最后
        buffer = self.raw_history.get_history()[self.history_window * -1:]
        for msg in buffer:
            messages.append(msg.buildMessage())
        
        return messages
