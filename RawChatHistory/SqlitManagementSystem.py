from __future__ import annotations
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from DataClass.ChatMessage import ChatMessage
from DataClass.DialogueMessage import DialogueMessage

from RawChatHistory.sqlit.ChatCrud import ChatCrud
from RawChatHistory.sqlit.DialogueCrud import DialogueCrud


class SqlitManagementSystem:
    """
    Facade 层：
    - 内部使用 ChatStore / DialogueStore
    - 自己不碰 ORM
    """

    def __init__(self, db_path: str, echo: bool = False):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=echo, future=True)

        self.SessionLocal = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )

        # 两个 store
        self.chat_store = ChatCrud(self.engine, self.SessionLocal)
        self.dialogue_store = DialogueCrud(self.engine, self.SessionLocal)

        # 建表
        self.chat_store.create_tables()

    # =====================
    # ChatMessage
    # =====================
    def getHistoryLength(self) -> int:
        """消息总数"""
        msgs = self.chat_store.list_messages(limit=1_000_000, with_analyze=False)
        return len(msgs)

    def getHistory(self, length: int) -> List[ChatMessage]:
        return self.chat_store.list_messages(
            limit=length,
            order_desc=True,
            with_analyze=True,
        )[::-1]

    def addMessage(self, message: ChatMessage) -> int:
        return self.chat_store.insert_message(message)

    def deleteMessageById(self, chat_turn_id: int):
        self.chat_store.delete_message(chat_turn_id)

    # =====================
    # Dialogue
    # =====================
    def getDialogues(self, length: int) -> List[DialogueMessage]:
        return self.dialogue_store.list(limit=length)[::-1]

    def getDialoguesById(self, dialogue_id: int) -> Optional[DialogueMessage]:
        return self.dialogue_store.get(dialogue_id)

    def updateDialogue(self, dialogue: DialogueMessage):
        if dialogue.dialogue_id is None:
            return

        # summary
        self.dialogue_store.update_summary(
            dialogue.dialogue_id,
            dialogue.summary,
        )

        # completed
        if dialogue.is_completed and dialogue.end_turn_id is not None:
            self.dialogue_store.mark_completed(
                dialogue.dialogue_id,
                dialogue.end_turn_id,
            )

    def addDialogue(self, dialogue: DialogueMessage) -> int:
        return self.dialogue_store.create(dialogue)

    # =====================
    def exit(self):
        self.engine.dispose()
