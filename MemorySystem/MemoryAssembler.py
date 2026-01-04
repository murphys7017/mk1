
from MemorySystem.MemoryStore.MemoryStorage import MemoryStorage
from MessageModel import ChatMessage
from loguru import logger

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
    def build_dialogue_prompt(self,user_input) -> str:
        dialogues = self.strorage.getDialogue(user_input)
        summary = ""
        i= 1
        for msg in dialogues:
            if msg is None:
                break
            summary += f"[{i}] {msg.summary}\n"
            i += 1
        dialogues_prompt = f"""
下面是目前的短期对话摘要：
{summary if summary != "" else "（无）"}
请基于以上内容，结合用户的对话输入，进行回复。

"""
        return dialogues_prompt


    def assemble(self, user_input: ChatMessage) -> list[dict]:

        identity_prompt = self.strorage.getIdentity()
        buffer = self.raw_history.get_history()[self.history_window *-1 :]
        dialogues_prompt = self.build_dialogue_prompt(user_input)

        messages = [{"role": "system", "content": identity_prompt},{"role": "system", "content": dialogues_prompt}]
        for msg in buffer:
            messages.append(msg.buildMessage())
        return messages