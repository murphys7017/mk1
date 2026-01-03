from typing import Optional, Literal
import time
from dataclasses import dataclass
import json

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
	
	def buildContent(self):
		if self.media_type=="text":
			content = f"""
				原始文本: {self.content}
				是否是问题：{self.extra.get("is_question", False) if self.extra else False}
				是否自我引用：{self.extra.get("is_self_reference", False) if self.extra else False}
				提及的实体：{', '.join(self.extra.get("mentioned_entities", []) ) if self.extra else ''}
				情感线索：{', '.join(self.extra.get("emotional_cues", []) ) if self.extra else ''}
			"""
			return content
		else:
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
