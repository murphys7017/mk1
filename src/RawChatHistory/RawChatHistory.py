import json
from DataClass.ChatMessage import ChatMessage
from DataClass.DialogueMessage import DialogueMessage
from pathlib import Path
from loguru import logger
import os

from RawChatHistory.SqlitManagementSystem import SqlitManagementSystem

class RawChatHistory:
    def __init__(self, history_length: int, dialogue_length: int , db_path:str , echo:bool = False):

        self.sql_manager = SqlitManagementSystem(db_path=db_path, echo=echo)
        self.history_length = history_length
        self.dialogue_length = dialogue_length

        self.historys: list[ChatMessage] = self.sql_manager.getHistory(history_length)
        self.dialogues: list[DialogueMessage] = self.sql_manager.getDialogues(dialogue_length)

    def getHistory(self,length = -1) -> list[ChatMessage]:
        if length == -1:
            length = self.history_length
        if len(self.historys) >= length:
            return self.historys[-length:]
        return self.sql_manager.getHistory(length)
    def getHistoryByRole(self,role:str, length = -1, sender_id: int | None = None) -> list[ChatMessage]:
        """
        获取指定角色的历史消息
        Args:
            role (str): 角色名称
            length (int, optional): 获取的消息数量. Defaults to -1.
        Returns:
            list[ChatMessage]: 指定角色的历史消息列表
        """
        if length == -1:
            length = self.history_length

        # 首先从内存缓存中过滤出符合 role 的消息（保留时间顺序）
        filtered = [m for m in self.historys if getattr(m, "role", None) == role]
        if len(filtered) >= length:
            return filtered[-length:]

        # 缓存不足，则从 DB 拉取指定 role（和 sender_id，如有） 的更多消息
        remaining = length - len(filtered)
        if sender_id is None:
            db_messages = self.sql_manager.getHistoryByRole(role, remaining)
        else:
            db_messages = self.sql_manager.getHistoryByRoleAndSender(role, sender_id, remaining)

        # 合并并按时间排序（确保时间顺序正确）
        combined = filtered + db_messages
        combined.sort(key=lambda m: getattr(m, "timestamp", 0))

        # 返回最新的 length 条（按时间正序）
        return combined[-length:]
    
    def getHistoryLength(self) -> int:
        return self.sql_manager.getHistoryLength()
    
    def getDialogueById(self, dialogue_id: int) -> DialogueMessage|None:
        return self.sql_manager.getDialoguesById(dialogue_id)
    
    def getDialogues(self, length: int = -1) -> list:
        if length == -1:
            length = self.dialogue_length
        if len(self.dialogues) >= length:
            return self.dialogues[-length:]
        return self.sql_manager.getDialogues(length)
    
    def updateDialogue(self, dialogue: DialogueMessage):
        res = self.sql_manager.updateDialogue(dialogue)
        self.dialogues = [d for d in self.dialogues if d.dialogue_id != dialogue.dialogue_id]
        self.dialogues.append(dialogue)
        self.dialogues = self.dialogues[-self.dialogue_length:]
        return res
    
    def addDialogues(self, dialogue: DialogueMessage):
        self.dialogues.append(dialogue)
        self.dialogues = self.dialogues[-self.dialogue_length:]
        return self.sql_manager.addDialogue(dialogue)

    def addMessage(self, message: ChatMessage):
        turn_id = self.sql_manager.addMessage(message)

        # 回填自增主键到内存对象，避免后续流程依赖 chat_turn_id 时拿到 None
        message.chat_turn_id = turn_id
        if message.analyze_result is not None:
            message.analyze_result.turn_id = turn_id

        self.historys.append(message)
        self.historys = self.historys[-self.history_length:]
        return turn_id
    
    def deleteMessageById(self, chat_turn_id: int):
        # 先删 DB，再同步清理内存缓存
        res = self.sql_manager.deleteMessageById(chat_turn_id)
        try:
            self.historys = [m for m in self.historys if m.chat_turn_id != chat_turn_id]
        except Exception:
            pass
        return res
        
    