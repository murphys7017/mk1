
from LocalModelFunc import LocalModelFunc
from MessageModel import ChatState
from RawChatHistory import RawChatHistory
from SystemPrompt import SystemPrompt
from tools import tools


class ChatStateStorage:
    """
    管理：
    - 原始对话（短期）
    - 已压缩摘要（中长期）
    """

    def __init__(
        self,
        raw_history: RawChatHistory,
        local_model_func: LocalModelFunc,
        # 最大长度
        history_window: int = 4,
        
    ):
        self.raw_history = raw_history
        self.local_model_func = local_model_func
        self.history_window = history_window

        self.activated_turn = 0
        self.chat_state: ChatState


    
    def activate_update_state(self):
        chat_buffer = self.raw_history.getHistory()[ -self.history_window :]
        buffer_text = " "
   
        for msg in chat_buffer:
            buffer_text += f"[{msg.chat_turn_id}] role:{msg.role} content:{msg.content}\n"
        input_text = SystemPrompt.judgeChatStatePrompt().format(
            dialogue_turns=buffer_text)
        input_text = tools.normalizeBlock(input_text)
        # === 2. 调用 Ollama（示意） ===
        model = SystemPrompt.judgeChatStateModel()
        options = {"temperature": 0, "top_p": 1}

        data = self.local_model_func._call_ollama_api(input_text, model, options)
        # logger.debug(f"Judge Dialogue Summary Response: {data}")

        if data is not None:
            self.chat_state = ChatState.from_dict(data)
            self.activated_turn = self.raw_history.getHistory()[-1].chat_turn_id
    
    def checkAndUpdateState(self):
        if self.raw_history.getHistory()[-1].chat_turn_id - self.activated_turn > self.history_window:
            self.activate_update_state()
    
    def getChatState(self) -> ChatState:
        return self.chat_state