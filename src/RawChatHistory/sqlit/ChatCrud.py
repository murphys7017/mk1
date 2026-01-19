from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Union, Type

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import sessionmaker, selectinload

from DataClass.ChatMessage import ChatMessage
from DataClass.AnalyzeResult import AnalyzeResult, Entity, Frame, Argument, Relation

from RawChatHistory.sqlit.SqiltModel import (
    Base,
    ChatMessageORM,
    AnalyzeResultORM,
    EntityORM,
    FrameORM,
    ArgumentORM,
    RelationORM,
)


SessionFactory = Union[Type[SASession], sessionmaker]


class ChatCrud:
    """
    负责 ChatMessage + 可选 AnalyzeResult 的存取。
    - 插入 message 时：AnalyzeResult 为空就不插
    - 读取 message 时：自动组装 message.analyze_result（可能 None）
    """

    def __init__(self, engine: Engine, SessionLocal: SessionFactory):
        self.engine = engine
        self.SessionLocal = SessionLocal

    def _session(self) -> SASession:
        if isinstance(self.SessionLocal, sessionmaker):
            return self.SessionLocal()
        return self.SessionLocal(bind=self.engine)  # type: ignore[arg-type]

    def create_tables(self) -> None:
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        Base.metadata.drop_all(self.engine)

    # =========================
    # dataclass -> ORM
    # =========================
    @staticmethod
    def _chat_to_orm(msg: ChatMessage) -> ChatMessageORM:
        return ChatMessageORM(
            sender_name=msg.sender_name,
            sender_id=msg.sender_id,
            role=msg.role,
            content=msg.content,
            timestamp=msg.timestamp,
            timedate=msg.timedate,
            extra=msg.extra,
            voice=msg.voice,
            image=msg.image,
            video=msg.video,
        )

    @staticmethod
    def _analyze_to_orm(ar: AnalyzeResult, *, turn_id: int) -> AnalyzeResultORM:
        row = AnalyzeResultORM(
            turn_id=turn_id,
            timestamp=ar.timestamp,
            media_type=ar.media_type,
            schema_version=ar.schema_version,
            normalized_text=ar.normalized_text,
            tokens=ar.tokens,
            keywords=ar.keywords,
            emotion_cues=ar.emotion_cues,
            is_question=ar.is_question,
            is_self_reference=ar.is_self_reference,
            raw=ar.raw,
        )

        # children: entities
        for e in ar.entities:
            row.entities.append(
                EntityORM(eid=getattr(e, "eid", None), text=e.text, typ=e.typ, span=e.span)
            )

        # children: frames + arguments
        for f in ar.frames:
            frow = FrameORM(predicate=f.predicate, predicate_span=f.predicate_span)
            for a in f.arguments:
                frow.arguments.append(
                    ArgumentORM(role=a.role, text=a.text, entity_ref=a.entity_ref, span=a.span)
                )
            row.frames.append(frow)

        # children: relations
        for r in ar.relations:
            row.relations.append(
                RelationORM(subject=r.subject, relation=r.relation, obj=r.obj)
            )

        return row

    # =========================
    # ORM -> dataclass
    # =========================
    @staticmethod
    def _analyze_to_dataclass(ar_row: AnalyzeResultORM) -> AnalyzeResult:
        entities = [
            Entity(text=e.text, typ=e.typ, span=e.span)
            for e in (ar_row.entities or [])
        ]

        frames: List[Frame] = []
        for f in (ar_row.frames or []):
            args = [
                Argument(role=a.role, text=a.text, entity_ref=a.entity_ref, span=a.span)
                for a in (f.arguments or [])
            ]
            frames.append(Frame(predicate=f.predicate, predicate_span=f.predicate_span, arguments=args))

        relations = [
            Relation(subject=r.subject, relation=r.relation, obj=r.obj)
            for r in (ar_row.relations or [])
        ]

        return AnalyzeResult(
            turn_id=ar_row.turn_id,
            timestamp=ar_row.timestamp,
            media_type=ar_row.media_type,
            schema_version=ar_row.schema_version,
            entities=entities,
            frames=frames,
            tokens=[
                (str(x[0]), str(x[1])) if isinstance(x, (list, tuple)) and len(x) >= 2 else (str(x), "")
                for x in (ar_row.tokens or [])
            ],
            keywords=ar_row.keywords or [],
            relations=relations,
            normalized_text=ar_row.normalized_text,
            is_question=ar_row.is_question,
            is_self_reference=ar_row.is_self_reference,
            emotion_cues=ar_row.emotion_cues or [],
            raw=ar_row.raw or {},
        )

    @staticmethod
    def _chat_to_dataclass(chat_row: ChatMessageORM) -> ChatMessage:
        ar_dc: Optional[AnalyzeResult] = None
        if chat_row.analyze_result is not None:
            ar_dc = ChatCrud._analyze_to_dataclass(chat_row.analyze_result)

        # Ensure role is one of the allowed literals
        role_value = chat_row.role
        if role_value not in ('user', 'assistant', 'system'):
            raise ValueError(f"Invalid role value: {role_value}")

        default_name, default_id = ChatMessage._default_sender_for_role(role_value)
        sender_name = getattr(chat_row, "sender_name", None) or default_name
        sender_id = getattr(chat_row, "sender_id", None)
        sender_id = int(sender_id) if sender_id is not None else default_id

        return ChatMessage(
            sender_name=sender_name,
            sender_id=sender_id,
            role=role_value,  # type: ignore
            content=chat_row.content,
            timestamp=chat_row.timestamp,
            timedate=chat_row.timedate,
            extra=chat_row.extra,
            chat_turn_id=chat_row.chat_turn_id,
            voice=chat_row.voice,
            image=chat_row.image,
            video=chat_row.video,
            analyze_result=ar_dc,
        )

    # =========================
    # Create
    # =========================
    def insert_message(self, msg: ChatMessage) -> int:
        """
        插入 ChatMessage；msg.analyze_result 不为空才插入 AnalyzeResult。
        返回 chat_turn_id（自增主键）。
        """
        with self._session() as session:
            chat_row = self._chat_to_orm(msg)
            session.add(chat_row)
            session.flush()  # 生成 chat_row.chat_turn_id

            turn_id = int(chat_row.chat_turn_id)

            if msg.analyze_result is not None:
                ar_row = self._analyze_to_orm(msg.analyze_result, turn_id=turn_id)
                session.add(ar_row)

            session.commit()
            return turn_id

    # =========================
    # Read (组合返回 dataclass)
    # =========================
    def get_message(self, chat_turn_id: int, *, with_analyze: bool = True) -> Optional[ChatMessage]:
        """
        读取一条消息，返回 ChatMessage dataclass（analyze_result 可能为 None）
        """
        with self._session() as session:
            stmt = select(ChatMessageORM).where(ChatMessageORM.chat_turn_id == chat_turn_id)

            if with_analyze:
                stmt = stmt.options(
                    selectinload(ChatMessageORM.analyze_result)
                        .selectinload(AnalyzeResultORM.entities),
                    selectinload(ChatMessageORM.analyze_result)
                        .selectinload(AnalyzeResultORM.relations),
                    selectinload(ChatMessageORM.analyze_result)
                        .selectinload(AnalyzeResultORM.frames)
                        .selectinload(FrameORM.arguments),
                )
            row = session.execute(stmt).scalar_one_or_none()
            if row is None:
                return None
            return self._chat_to_dataclass(row)

    def list_messages(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        order_desc: bool = True,
        with_analyze: bool = True,
        role: Optional[str] = None,
        sender_id: Optional[int] = None,
    ) -> List[ChatMessage]:
        """
        列表查询（可选按 role 过滤），返回 ChatMessage dataclass 列表
        """
        with self._session() as session:
            stmt = select(ChatMessageORM)

            if role is not None:
                stmt = stmt.where(ChatMessageORM.role == role)

            if sender_id is not None:
                stmt = stmt.where(ChatMessageORM.sender_id == int(sender_id))

            stmt = stmt.order_by(
                ChatMessageORM.chat_turn_id.desc() if order_desc else ChatMessageORM.chat_turn_id.asc()
            ).limit(limit).offset(offset)

            if with_analyze:
                stmt = stmt.options(
                    selectinload(ChatMessageORM.analyze_result)
                        .selectinload(AnalyzeResultORM.entities),
                    selectinload(ChatMessageORM.analyze_result)
                        .selectinload(AnalyzeResultORM.relations),
                    selectinload(ChatMessageORM.analyze_result)
                        .selectinload(AnalyzeResultORM.frames)
                        .selectinload(FrameORM.arguments),
                )

            rows = session.execute(stmt).scalars().all()
            return [self._chat_to_dataclass(r) for r in rows]

    # =========================
    # Delete
    # =========================
    def delete_message(self, chat_turn_id: int) -> bool:
        """
        删除 ChatMessage；AnalyzeResult 会 CASCADE 自动删除
        """
        with self._session() as session:
            row = session.get(ChatMessageORM, chat_turn_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    # =========================
    # Optional helpers
    # =========================
    def attach_or_replace_analyze(self, chat_turn_id: int, ar: AnalyzeResult) -> bool:
        """
        给已有 ChatMessage 补写/覆盖 AnalyzeResult（比如异步分析后回填）。
        - 若已有 analyze_result：覆盖（先删旧再插新）
        """
        with self._session() as session:
            chat_row = session.get(ChatMessageORM, chat_turn_id)
            if chat_row is None:
                return False

            # 删除旧（如果存在）
            if chat_row.analyze_result is not None:
                session.delete(chat_row.analyze_result)
                session.flush()

            ar_row = self._analyze_to_orm(ar, turn_id=chat_turn_id)
            session.add(ar_row)
            session.commit()
            return True

    def remove_analyze(self, chat_turn_id: int) -> bool:
        """删除某条消息的 AnalyzeResult（提醒：消息本身不删）"""
        with self._session() as session:
            stmt = select(AnalyzeResultORM).where(AnalyzeResultORM.turn_id == chat_turn_id)
            ar_row = session.execute(stmt).scalar_one_or_none()
            if ar_row is None:
                return False
            session.delete(ar_row)
            session.commit()
            return True
