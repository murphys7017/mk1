
from LLM.LLMManagement import LLMManagement
from DataClass.ChatState import ChatState
from RawChatHistory.RawChatHistory import RawChatHistory
from SystemPrompt import SystemPrompt
from tools import tools
from loguru import logger
from ChatStateSystem.ChatStateSystem import ChatStateSystem

class DefaultChatStateSystem(ChatStateSystem):
    """
    管理：
    - 原始对话（短期）
    - 已压缩摘要（中长期）
    """

    def __init__(
        self,
        raw_history: RawChatHistory,
        llm_management: LLMManagement,
        system_prompt: SystemPrompt,
        # 最大长度
        history_window: int,
        
    ):
        self.raw_history = raw_history
        self.llm_management = llm_management
        self.system_prompt = system_prompt
        self.history_window = history_window

        self.activated_turn = 0
        self.chat_state: ChatState = ChatState(
                                    interaction = "闲聊",
                                    user_attitude = "积极",
                                    emotional_state = "平静",
                                    leading_approach = "用户主导"
                                    )


    def getState(self) -> ChatState:
        return self.chat_state
    
    def activate_update_state(self):
        chat_buffer = self.raw_history.getHistory(self.history_window)
        buffer_text = " "
   
        for msg in chat_buffer:
            buffer_text += f"[{msg.chat_turn_id}] role:{msg.role} content:{msg.content}\n"

        data = self.llm_management.generate(
            prompt_name ='judge_chat_state', 
            options = {"temperature": 0, "top_p": 1},
            dialogue_turns=buffer_text)
  
        logger.debug(f"Judge Dialogue Summary Response: {data}")

        if data is not None:
            data['updated_at'] =chat_buffer[0].chat_turn_id
            self.chat_state = ChatState.from_dict(data)
            self.activated_turn = chat_buffer[0].chat_turn_id
    
    def checkAndUpdateState(self, turn_id: int):
        if turn_id is not None and self.activated_turn is not None:
            if turn_id - self.activated_turn > self.history_window:
                self.activate_update_state()
    
    def assemble(self) -> str:
        return self.chat_state.to_prompt()