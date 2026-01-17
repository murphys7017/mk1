from typing import Optional, Literal
import time
from dataclasses import dataclass
import json

from DataClass.AnalyzeResult import Entity

@dataclass
class DialogueMessage:

	start_turn_id: int
	summary: str
	is_completed: bool = False

	# 新增用于检索的字段
	entities: Optional[list[Entity]] = None
	keywords: Optional[list[str]] = None
	emotion_cues: Optional[list] = None

	# 持久化字段
	dialogue_id: Optional[int] = None
	dialogue_turns: Optional[int] = None
	end_turn_id: Optional[int] = None


	def to_json(self) -> str:

			return json.dumps({
				"dialogue_id": self.dialogue_id,
				"dialogue_turns": self.dialogue_turns,
				"start_turn_id": self.start_turn_id,
				"end_turn_id": self.end_turn_id,
				"is_completed": self.is_completed,
				"summary": self.summary,
				"entities": self.entities or [],
				"keywords": self.keywords or [],
				"emotion_cues": self.emotion_cues or []
				}, ensure_ascii=False)
	
	@staticmethod
	def from_dict(data: dict):
		return DialogueMessage(
			start_turn_id=data.get("start_turn_id", 0),
			summary=data.get("summary", ""),
			is_completed=data.get("is_completed", False),
			entities=data.get("entities", None),
			keywords=data.get("keywords", None),
			emotion_cues=data.get("emotion_cues", None),
			dialogue_id=data.get("dialogue_id", None),
			dialogue_turns=data.get("dialogue_turns", None),
			end_turn_id=data.get("end_turn_id", None)
		)
