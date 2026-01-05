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
	chat_turn_id: Optional[int] = None

	CHAT_TAG = "CHAT_MESSAGE"
	RAW_TEXT_TAG = "RAW_TEXT"
	IS_QUESTION_TAG = "IS_QUESTION"
	IS_SELF_REFERENCE_TAG = "IS_SELF_REFERENCE"
	MENTIONED_ENTITIES_TAG = "MENTIONED_ENTITIES"
	EMOTIONAL_CUES_TAG = "EMOTIONAL_CUES"
	def buildContentBK(self):
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
			return tools.normalizeBlock(content)
		else:
			return tools.normalizeBlock(self.content)
	
	def getExtra(self):
		return self.extra if self.extra else {}

	def buildContent(self):
		if self.media_type=="text":
			content = self.content
			return tools.normalizeBlock(content)
		else:
			return tools.normalizeBlock(self.content)
	
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
			media_type=data["media_type"],
			extra=data.get("extra", None),
			chat_turn_id=data.get("chat_turn_id", None)
		)

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

	def to_json(self) -> str:

			return json.dumps({
					"interaction": self.interaction,
					"user_attitude": self.user_attitude,
					"emotional_state": self.emotional_state,
					"leading_approach": self.leading_approach
				}, ensure_ascii=False)
	
	def from_json(self, json_str: str):
		data = json.loads(json_str)
		self.interaction = data.get("interaction", "其他")
		self.user_attitude = data.get("user_attitude", "中立")
		self.emotional_state = data.get("emotional_state", "平静")
		self.leading_approach = data.get("leading_approach", "平等互动")
	@staticmethod
	def from_dict(data: dict):
		return ChatState(
			interaction=data.get("interaction", "其他"),
			user_attitude=data.get("user_attitude", "中立"),
			emotional_state=data.get("emotional_state", "平静"),
			leading_approach=data.get("leading_approach", "平等互动")
		)