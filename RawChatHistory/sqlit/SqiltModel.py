from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    BigInteger,
    String,
    Text,
    event,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


# --- SQLite: enable foreign key constraints (CASCADE works) ---
@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


class Base(DeclarativeBase):
    pass

class DialogueMessageORM(Base):
    __tablename__ = "dialogue_messages"

    # 对齐 dataclass
    dialogue_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    start_turn_id: Mapped[int] = mapped_column(Integer, index=True)
    end_turn_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)

    summary: Mapped[str] = mapped_column(Text)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    dialogue_turns: Mapped[Optional[int]] = mapped_column(Integer)

Index("ix_dialogue_range", 
      DialogueMessageORM.start_turn_id, 
      DialogueMessageORM.end_turn_id)


class ChatMessageORM(Base):
    __tablename__ = "chat_messages"

    # 对齐 dataclass: chat_turn_id
    chat_turn_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    role: Mapped[str] = mapped_column(String(16), index=True)  # user|assistant|system
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[int] = mapped_column(BigInteger, index=True)  # ms
    timedate: Mapped[str] = mapped_column(String(32), index=True)

    extra: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    voice: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    image: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    video: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)

    # 1:1 optional
    analyze_result: Mapped[Optional["AnalyzeResultORM"]] = relationship(
        back_populates="chat_message",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


Index("ix_chat_messages_role_time", ChatMessageORM.role, ChatMessageORM.timestamp)


class AnalyzeResultORM(Base):
    __tablename__ = "analyze_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 对齐 dataclass: turn_id
    # 绑定 chat_messages.chat_turn_id；1:1 用 UNIQUE
    turn_id: Mapped[int] = mapped_column(
        ForeignKey("chat_messages.chat_turn_id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    timestamp: Mapped[Optional[int]] = mapped_column(BigInteger, index=True)  # ms
    media_type: Mapped[str] = mapped_column(String(32), default="text")
    schema_version: Mapped[str] = mapped_column(String(32), default="analyze_v1")

    normalized_text: Mapped[Optional[str]] = mapped_column(Text)

    tokens: Mapped[List[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[List[str]] = mapped_column(JSON, default=list)
    emotion_cues: Mapped[List[str]] = mapped_column(JSON, default=list)

    is_question: Mapped[Optional[bool]] = mapped_column(Boolean)
    is_self_reference: Mapped[Optional[bool]] = mapped_column(Boolean)

    raw: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    # backref to ChatMessage
    chat_message: Mapped["ChatMessageORM"] = relationship(
        back_populates="analyze_result",
        uselist=False,
    )

    # children
    entities: Mapped[List["EntityORM"]] = relationship(
        back_populates="analyze_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    frames: Mapped[List["FrameORM"]] = relationship(
        back_populates="analyze_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    relations: Mapped[List["RelationORM"]] = relationship(
        back_populates="analyze_result",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class EntityORM(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analyze_result_id: Mapped[int] = mapped_column(
        ForeignKey("analyze_results.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    eid: Mapped[Optional[str]] = mapped_column(String(32), index=True)  # "E1"
    text: Mapped[Optional[str]] = mapped_column(Text, index=True)
    typ: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    span: Mapped[Optional[List[int]]] = mapped_column(JSON)

    analyze_result: Mapped["AnalyzeResultORM"] = relationship(back_populates="entities")


class FrameORM(Base):
    __tablename__ = "frames"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analyze_result_id: Mapped[int] = mapped_column(
        ForeignKey("analyze_results.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    predicate: Mapped[str] = mapped_column(Text, index=True)
    predicate_span: Mapped[Optional[List[int]]] = mapped_column(JSON)

    analyze_result: Mapped["AnalyzeResultORM"] = relationship(back_populates="frames")
    arguments: Mapped[List["ArgumentORM"]] = relationship(
        back_populates="frame",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ArgumentORM(Base):
    __tablename__ = "arguments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    frame_id: Mapped[int] = mapped_column(
        ForeignKey("frames.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    role: Mapped[str] = mapped_column(String(32), index=True)
    text: Mapped[str] = mapped_column(Text)
    entity_ref: Mapped[Optional[str]] = mapped_column(String(32), index=True)  # Entity.eid
    span: Mapped[Optional[List[int]]] = mapped_column(JSON)

    frame: Mapped["FrameORM"] = relationship(back_populates="arguments")


class RelationORM(Base):
    __tablename__ = "relations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analyze_result_id: Mapped[int] = mapped_column(
        ForeignKey("analyze_results.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    subject: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    relation: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    obj: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    analyze_result: Mapped["AnalyzeResultORM"] = relationship(back_populates="relations")


Index("ix_entities_result_eid", EntityORM.analyze_result_id, EntityORM.eid, unique=False)
Index("ix_relations_spo", RelationORM.subject, RelationORM.relation, RelationORM.obj, unique=False)
