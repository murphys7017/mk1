from typing import Optional, Literal
from dataclasses import dataclass
import json
from typing import Any
from tools import tools
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
	extra: Optional[dict] = None
	chat_turn_id: Optional[int] = None
	voice: Optional[Any] = None
	image: Optional[Any] = None
	video: Optional[Any] = None

	CHAT_TAG = "CHAT_MESSAGE"
	RAW_TEXT_TAG = "RAW_TEXT"
	IS_QUESTION_TAG = "IS_QUESTION"
	IS_SELF_REFERENCE_TAG = "IS_SELF_REFERENCE"
	MENTIONED_ENTITIES_TAG = "MENTIONED_ENTITIES"
	EMOTIONAL_CUES_TAG = "EMOTIONAL_CUES"

	def buildContentBK(self):
			content = f"""
				<{self.CHAT_TAG}>
				<{self.RAW_TEXT_TAG}>
					{self.content}
				</{self.RAW_TEXT_TAG}>
				<{self.IS_QUESTION_TAG}>
					{self.extra.get("is_question", False) if self.extra else False}
				</{self.IS_QUESTION_TAG}>
				<{self.IS_SELF_REFERENCE_TAG}>
					{self.extra.get("is_self_reference", False) if self.extra else False}
				</{self.IS_SELF_REFERENCE_TAG}>
				<{self.MENTIONED_ENTITIES_TAG}>
					{', '.join(self.extra.get("mentioned_entities", []) ) if self.extra else ''}
				</{self.MENTIONED_ENTITIES_TAG}>
				<{self.EMOTIONAL_CUES_TAG}>
					{', '.join(self.extra.get("emotional_cues", []) ) if self.extra else ''}
				</{self.EMOTIONAL_CUES_TAG}>
				</{self.CHAT_TAG}>
			"""
			return tools.normalizeBlock(content)
	
	def getExtra(self):
		return self.extra if self.extra else {}

	def buildContent(self):
		return self.content

	
	def buildMessage(self):
		return {
			"role": self.role,
			"content": self.buildContent(),
		}
	def to_json(self) -> str:

		return json.dumps({
				"role": self.role,
				"content": self.content,
				"timestamp": self.timestamp,
				"timedate": self.timedate,
				"extra": self.extra,
				"chat_turn_id": self.chat_turn_id
			}, ensure_ascii=False)
	@staticmethod
	def from_dict(data: dict):
		return ChatMessage(
			role=data["role"],
			content=data["content"],
			timestamp=data["timestamp"],
			timedate=data["timedate"],
			extra=data.get("extra", None),
			chat_turn_id=data.get("chat_turn_id", None)
		)
