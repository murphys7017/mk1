from typing import Optional, Literal
import time
from dataclasses import dataclass
import json

@dataclass
class ChatState:
	"""
	{
		"interaction": "闲聊" | "问答" | "角色扮演" | "信息提供" | "任务协助" | "其他",
		"user_attitude": "积极" | "中立" | "消极",
		"emotional_state": "平静" | "激动" | "沮丧" | "愉快" | "紧张" | "其他",
		"leading_approach": "用户主导" | "AI主导" | "平等互动"
	}
	"""
	interaction: str
	user_attitude: str
	emotional_state: str
	leading_approach: str
	updated_at: Optional[int] = None  # 对话轮数

	def to_json(self) -> str:

			return json.dumps({
					"interaction": self.interaction,
					"user_attitude": self.user_attitude,
					"emotional_state": self.emotional_state,
					"leading_approach": self.leading_approach,
					"updated_at": self.updated_at
				}, ensure_ascii=False)
	
	def from_json(self, json_str: str):
		data = json.loads(json_str)
		self.interaction = data.get("interaction", "其他")
		self.user_attitude = data.get("user_attitude", "中立")
		self.emotional_state = data.get("emotional_state", "平静")
		self.leading_approach = data.get("leading_approach", "平等互动")
		self.updated_at = data.get("updated_at", None)
	@staticmethod
	def from_dict(data: dict):
		return ChatState(
			interaction=data.get("interaction", "其他"),
			user_attitude=data.get("user_attitude", "中立"),
			emotional_state=data.get("emotional_state", "平静"),
			leading_approach=data.get("leading_approach", "平等互动"),
			updated_at=data.get("updated_at", None)
		)