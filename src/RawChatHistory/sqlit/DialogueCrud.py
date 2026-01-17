from typing import Optional, List, Union, Type
from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SASession
from sqlalchemy.orm import sessionmaker

from DataClass.DialogueMessage import DialogueMessage
from RawChatHistory.sqlit.SqiltModel import Base, DialogueMessageORM


SessionFactory = Union[Type[SASession], sessionmaker]


class DialogueCrud:

    def __init__(self, engine: Engine, SessionLocal: SessionFactory):
        self.engine = engine
        self.SessionLocal = SessionLocal

    def _session(self) -> SASession:
        if isinstance(self.SessionLocal, sessionmaker):
            return self.SessionLocal()
        return self.SessionLocal(bind=self.engine)

    # ---------- helpers ----------
    @staticmethod
    def _to_orm(dm: DialogueMessage) -> DialogueMessageORM:
        return DialogueMessageORM(
            start_turn_id=dm.start_turn_id,
            end_turn_id=dm.end_turn_id,
            summary=dm.summary,
            is_completed=dm.is_completed,
            dialogue_turns=dm.dialogue_turns,
            entities=dm.entities or [],
            keywords=dm.keywords or [],
            emotion_cues=dm.emotion_cues or [],
        )

    @staticmethod
    def _to_dataclass(row: DialogueMessageORM) -> DialogueMessage:
        return DialogueMessage(
            start_turn_id=row.start_turn_id,
            end_turn_id=row.end_turn_id,
            summary=row.summary,
            is_completed=row.is_completed,
            entities=row.entities or [],
            keywords=row.keywords or [],
            emotion_cues=row.emotion_cues or [],
            dialogue_id=row.dialogue_id,
            dialogue_turns=row.dialogue_turns,
        )

    # ---------- CRUD ----------

    def create(self, dm: DialogueMessage) -> int:
        """新建对话"""
        with self._session() as session:
            row = self._to_orm(dm)
            session.add(row)
            session.commit()
            session.refresh(row)
            return int(row.dialogue_id)

    def get(self, dialogue_id: int) -> Optional[DialogueMessage]:
        with self._session() as session:
            row = session.get(DialogueMessageORM, dialogue_id)
            return self._to_dataclass(row) if row else None

    def list(self, *, limit=50, offset=0) -> List[DialogueMessage]:
        with self._session() as session:
            rows = session.execute(
                select(DialogueMessageORM)
                .order_by(DialogueMessageORM.dialogue_id.desc())
                .limit(limit)
                .offset(offset)
            ).scalars().all()

            return [self._to_dataclass(r) for r in rows]

    def mark_completed(self, dialogue_id: int, end_turn_id: int) -> bool:
        """结束对话"""
        with self._session() as session:
            res = session.execute(
                update(DialogueMessageORM)
                .where(DialogueMessageORM.dialogue_id == dialogue_id)
                .values(
                    is_completed=True,
                    end_turn_id=end_turn_id,
                )
            )
            session.commit()
            return (res.rowcount or 0) > 0 # type: ignore

    def update_summary(
        self,
        dialogue_id: int,
        summary: str,
        entities: Optional[list] = None,
        keywords: Optional[list] = None,
        emotion_cues: Optional[list] = None,
    ) -> bool:
        with self._session() as session:
            values = {"summary": summary}
            if entities is not None:
                values["entities"] = entities
            if keywords is not None:
                values["keywords"] = keywords
            if emotion_cues is not None:
                values["emotion_cues"] = emotion_cues

            res = session.execute(
                update(DialogueMessageORM)
                .where(DialogueMessageORM.dialogue_id == dialogue_id)
                .values(**values)
            )
            session.commit()
            return (res.rowcount or 0) > 0 # type: ignore

    def delete(self, dialogue_id: int) -> bool:
        with self._session() as session:
            row = session.get(DialogueMessageORM, dialogue_id)
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True
