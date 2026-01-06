from typing import Optional, Literal
import time
from dataclasses import dataclass
import json

@dataclass
class DialogueMessage:

	start_turn_id: int
	summary: str
	is_completed: bool = False
	

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
				"summary": self.summary
				}, ensure_ascii=False)
	
	@staticmethod
	def from_dict(data: dict):
		return DialogueMessage(
			start_turn_id=data.get("start_turn_id", 0),
			summary=data.get("summary", ""),
			is_completed=data.get("is_completed", False),
			dialogue_id=data.get("dialogue_id", None),
			dialogue_turns=data.get("dialogue_turns", None),
			end_turn_id=data.get("end_turn_id", None)
		)
