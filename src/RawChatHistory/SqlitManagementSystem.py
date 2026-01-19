from __future__ import annotations
from typing import List, Optional

from sqlalchemy import text
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

        # 轻量迁移：为旧 DB 补齐 chat_messages.sender_name / sender_id
        self._migrate_chat_messages_sender_fields()

    def _migrate_chat_messages_sender_fields(self) -> None:
        with self.engine.begin() as conn:
            try:
                cols = {
                    row["name"]
                    for row in conn.execute(text("PRAGMA table_info(chat_messages)")).mappings().all()
                }
            except Exception:
                return

            if "sender_name" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE chat_messages "
                        "ADD COLUMN sender_name TEXT NOT NULL DEFAULT ''"
                    )
                )
            if "sender_id" not in cols:
                conn.execute(
                    text(
                        "ALTER TABLE chat_messages "
                        "ADD COLUMN sender_id INTEGER NOT NULL DEFAULT 0"
                    )
                )

            # 回填：按 role 补齐空值
            conn.execute(
                text(
                    "UPDATE chat_messages "
                    "SET sender_name='Alice', sender_id=-1 "
                    "WHERE role='assistant' AND (sender_name='' OR sender_name IS NULL)"
                )
            )
            conn.execute(
                text(
                    "UPDATE chat_messages "
                    "SET sender_name='aki', sender_id=1 "
                    "WHERE role='user' AND (sender_name='' OR sender_name IS NULL)"
                )
            )
            conn.execute(
                text(
                    "UPDATE chat_messages "
                    "SET sender_name='system', sender_id=0 "
                    "WHERE role='system' AND (sender_name='' OR sender_name IS NULL)"
                )
            )

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
            entities=getattr(dialogue, "entities", None),
            keywords=getattr(dialogue, "keywords", None),
            emotion_cues=getattr(dialogue, "emotion_cues", None),
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
