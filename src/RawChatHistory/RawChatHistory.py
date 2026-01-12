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

    def getHistory(self,length = -1) -> list[ChatMessage]:
        if length == -1:
            length = self.history_length
        return self.sql_manager.getHistory(length)
    
    def getHistoryLength(self) -> int:
        return self.sql_manager.getHistoryLength()
    
    def getDialogueById(self, dialogue_id: int) -> DialogueMessage|None:
        return self.sql_manager.getDialoguesById(dialogue_id)
    
    def getDialogues(self, length: int = -1) -> list:
        if length == -1:
            length = self.dialogue_length
        return self.sql_manager.getDialogues(length)
    
    def updateDialogue(self, dialogue: DialogueMessage):
        return self.sql_manager.updateDialogue(dialogue)
    
    def addDialogues(self, dialogue: DialogueMessage):
        return self.sql_manager.addDialogue(dialogue)

    def addMessage(self, message: ChatMessage):
        return self.sql_manager.addMessage(message)
    def deleteMessageById(self, chat_turn_id: int):
        return self.sql_manager.deleteMessageById(chat_turn_id)
        
    