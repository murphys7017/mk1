import json
from MessageModel import ChatMessage, DialogueMessage
from pathlib import Path
from loguru import logger
import os

class RawChatHistoryFile:
    def __init__(self,
                 max_length: int = 100,
                 initial_load: bool = True,
                 initial_load_length: int = 30,
                 auto_save: bool = True,
                 chat_save_path: str = "raw_chat_history.txt",dialogue_save_path: str = "dialogue_history.txt"
                 ):
        self.max_length = max_length
        self.initial_load_length = initial_load_length
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
        
        self.load_history()

    def read_last_n_lines(self, file_path: Path, n):
        """
        高效从后往前读取文件最后n行，适合大文件，文本模式。
        """
        with file_path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            buffer = bytearray()
            lines = []
            pointer = file_size

            while pointer > 0 and len(lines) < n:
                pointer -= 1
                f.seek(pointer)
                byte = f.read(1)
                if byte == b'\n':
                    if buffer:
                        lines.append(buffer[::-1].decode('utf-8', errors='ignore'))
                        buffer = bytearray()
                else:
                    buffer.extend(byte)
            if buffer and len(lines) < n:
                lines.append(buffer[::-1].decode('utf-8', errors='ignore'))
            return lines[::-1]
    
    def load_history(self):

        for msg in self.read_last_n_lines(self.raw_save_file, self.initial_load_length):
            data = json.loads(msg.strip())
            message = ChatMessage.from_dict(data)
            self.raw_history.append(message)
        
        for dialogue in self.read_last_n_lines(self.dialogue_save_file, self.initial_load_length):
            data = json.loads(dialogue.strip())
            dialogue_message = DialogueMessage.from_dict(data)
            self.dialogue_history.append(dialogue_message)

    def getHistory(self) -> list:
        return self.raw_history
    def getHistoryLength(self) -> int:
        return len(self.raw_history)
    
    def getDialogueById(self, dialogue_id: int) -> DialogueMessage|None:
        for dialogue in self.dialogue_history:
            if dialogue.dialogue_id == dialogue_id:
                return dialogue
        return None
    
    def getDialogues(self, length: int) -> list:
        if length >= len(self.dialogue_history):
            return [None]
        if length > 1:
            res = []
            i = 0
            for dialogue in self.dialogue_history:
                    res.append(dialogue)
                    i += 1
                    if i >= length:
                        break
            return res
        else:
            return self.dialogue_history[-length:]
    def updateDialogue(self, dialogue: DialogueMessage):
        for i in range(len(self.dialogue_history)):
            if self.dialogue_history[i].dialogue_id == dialogue.dialogue_id:
                self.dialogue_history[i] = dialogue
                break
        # 重写文件
        with self.dialogue_save_file.open("w", encoding="utf-8") as f:
            for dlg in self.dialogue_history:
                f.write(dlg.to_json() + "\n")
    
    def addDialogues(self, dialogue: DialogueMessage):
        dialogue.dialogue_id = (self.dialogue_history[-1].dialogue_id + 1) if len(self.dialogue_history) > 0 and self.dialogue_history[-1].dialogue_id is not None else 1
        self.dialogue_history.append(dialogue)
        self.dialogue_history = self.dialogue_history[-self.max_length:]
        with self.dialogue_save_file.open("a", encoding="utf-8") as f:
            f.write(dialogue.to_json() + "\n")

    def addMessage(self, message: ChatMessage):
        if len(self.raw_history) == 0:
            message.chat_turn_id = 1
        else:
            if self.raw_history[-1].chat_turn_id is None:
                with self.raw_save_file.open("rb") as f:
                    message.chat_turn_id = len(f.readlines()) + 1
            else:
                message.chat_turn_id = self.raw_history[-1].chat_turn_id + 1
        self.raw_history.append(message)
        self.raw_history = self.raw_history[-self.max_length:]
        with self.raw_save_file.open("a", encoding="utf-8") as f:
            f.write(message.to_json() + "\n")
        
    