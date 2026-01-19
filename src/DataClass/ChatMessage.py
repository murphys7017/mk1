from typing import Optional, Literal
from dataclasses import dataclass
import json
from typing import Any
from DataClass.AnalyzeResult import AnalyzeResult
from DataClass.QuerySchema import QuerySchema
from tools.tools import tools
@dataclass
class ChatMessage:
	"""
	对话消息数据模型
	role: "user" | "assistant" | "system"
	content: 消息内容
	timestamp: 消息时间戳（毫秒）
	extra: 可选扩展字段
	"""
	role: Literal["user", "assistant", "system"]
	content: str
	timestamp: int
	timedate: str

	sender_name: str = ""
	sender_id: int = 0
	extra: Optional[dict] = None
	chat_turn_id: Optional[int] = None
	voice: Optional[Any] = None
	image: Optional[Any] = None
	video: Optional[Any] = None
	analyze_result: Optional[AnalyzeResult] = None
	query_schema: Optional[QuerySchema] = None


	def getExtra(self):
		return self.extra if self.extra else {}

	def buildContent(self):
		return self.content

	
	def buildMessage(self):
		return {
			"role": self.role,
			"content": self.buildContent(),
		}

	@staticmethod
	def _default_sender_for_role(role: str) -> tuple[str, int]:
		if role == "assistant":
			return ("Alice", -1)
		if role == "user":
			return ("aki", 1)
		return ("system", 0)
	def to_json(self) -> str:

		return json.dumps({
				"sender_name": self.sender_name,
				"sender_id": self.sender_id,
				"role": self.role,
				"content": self.content,
				"timestamp": self.timestamp,
				"timedate": self.timedate,
				"extra": self.extra,
				"chat_turn_id": self.chat_turn_id
			}, ensure_ascii=False)
	@staticmethod
	def from_dict(data: dict):
		role = data["role"]
		default_name, default_id = ChatMessage._default_sender_for_role(role)

		sender_name = data.get("sender_name", None) or default_name
		sender_id_raw = data.get("sender_id", None)
		try:
			sender_id = int(sender_id_raw) if sender_id_raw is not None else default_id
		except Exception:
			sender_id = default_id

		return ChatMessage(
			sender_name=sender_name,
			sender_id=sender_id,
			role=role,
			content=data["content"],
			timestamp=data["timestamp"],
			timedate=data["timedate"],
			extra=data.get("extra", None),
			chat_turn_id=data.get("chat_turn_id", None)
		)
