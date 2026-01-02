from MessageModel import ChatMessage, DialogueMessage
from pathlib import Path
from loguru import logger

class RawChatHistory:
    def __init__(self,
                 max_length: int = 100,
                 auto_save: bool = True,
                 chat_save_path: str = "raw_chat_history.txt",dialogue_save_path: str = "dialogue_history.txt"
                 ):
        self.max_length = max_length
        self.auto_save = auto_save

        self.raw_history: list[ChatMessage] = []
        self.raw_save_path = chat_save_path
        self.raw_save_file = Path(self.raw_save_path)
        if not self.raw_save_file.exists():
            self.raw_save_file.touch()
            logger.info("Raw chat history file created at {}".format(self.raw_save_path))
        else:
            logger.info("Raw chat history file exists at {}".format(self.raw_save_path))

        self.dialogue_history: list[DialogueMessage] = []
        self.dialogue_save_path = dialogue_save_path
        self.dialogue_save_file = Path(self.dialogue_save_path)
        if not self.dialogue_save_file.exists():
            self.dialogue_save_file.touch()
            logger.info("Dialogue history file created at {}".format(self.dialogue_save_path))
        else:
            logger.info("Dialogue history file exists at {}".format(self.dialogue_save_path))

    def get_history(self) -> list:
        return self.raw_history
    def get_dialogues(self, length: int) -> list:
        if length >= len(self.dialogue_history):
            return [None]
        if length > 1:
            res = []
            i = 0
            for dialogue in self.dialogue_history:
                if dialogue.end_timestamp is not None:
                    res.append(dialogue)
                    i += 1
                    if i >= length:
                        break
            return res
        else:
            return self.dialogue_history[-length:]
    
    def add_dialogue(self, dialogue: DialogueMessage):
        self.dialogue_history.append(dialogue)
        self.dialogue_history = self.dialogue_history[-self.max_length:]
        with self.dialogue_save_file.open("a", encoding="utf-8") as f:
            f.write(dialogue.to_json() + "\n")

    def add_message(self, message: ChatMessage):
        self.raw_history.append(message)
        self.raw_history = self.raw_history[-self.max_length:]
        with self.raw_save_file.open("a", encoding="utf-8") as f:
            f.write(message.to_json() + "\n")
        
    