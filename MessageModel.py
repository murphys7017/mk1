from typing import Optional, Literal
import time
from dataclasses import dataclass
import json
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
	media_type:Literal["text","image","audio","video"]
	extra: Optional[dict] = None

	CHAT_TAG = "CHAT_MESSAGE"
	RAW_TEXT_TAG = "RAW_TEXT"
	IS_QUESTION_TAG = "IS_QUESTION"
	IS_SELF_REFERENCE_TAG = "IS_SELF_REFERENCE"
	MENTIONED_ENTITIES_TAG = "MENTIONED_ENTITIES"
	EMOTIONAL_CUES_TAG = "EMOTIONAL_CUES"
	def buildContent(self):
		if self.media_type=="text":
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
			return tools.normalize_block(content)
		else:
			return tools.normalize_block(self.content)
	
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
				"media_type": self.media_type,
				"extra": self.extra
			}, ensure_ascii=False)

@dataclass
class DialogueMessage:
	start_timestamp: int
	start_timedate: str
	summary: str

	end_timestamp: Optional[int] = None
	end_timedate: Optional[str] = None

	def to_json(self) -> str:

			return json.dumps({
					"start_timestamp": self.start_timestamp,
					"start_timedate": self.start_timedate,
					"end_timestamp": self.end_timestamp if self.end_timestamp else 'NOTEND',
					"end_timedate": self.end_timedate if self.end_timedate else 'NOTEND',
					"summary": self.summary
				}, ensure_ascii=False)
