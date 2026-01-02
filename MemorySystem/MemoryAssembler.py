
from MemorySystem.MemoryStore.MemoryStorage import MemoryStorage
from MessageModel import ChatMessage
from loguru import logger

class MemoryAssembler:
    def __init__(self,strorage: MemoryStorage):
        self.strorage = strorage

    def build_dialogue_prompt(self,user_input) -> str:
        buffer,dialogues = self.strorage.getDialogue(user_input)
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


"""
        return buffer,dialogues_prompt


    def assemble(self, user_input: ChatMessage) -> str:

        identity_prompt = self.strorage.getIdentity()
        buffer, dialogues_prompt = self.build_dialogue_prompt(user_input)

        messages = [{"role": "system", "content": identity_prompt},{"role": "system", "content": dialogues_prompt}]
        for msg in buffer:
            messages.append(msg.buildMessage())
        return messages