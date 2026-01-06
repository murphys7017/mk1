
from LLM.LLMManagement import LLMManagement
from SystemPrompt import SystemPrompt
from MessageModel import ChatMessage, DialogueMessage
from loguru import logger
from tools import tools
class MemoryPolicy:
    """Memory policy for managing memory storage and retrieval.
    输入应为 对话的文本形式 话题的文本
    """

    def __init__(self, llm_management: LLMManagement):
         self.llm_management = llm_management
    
    def splitBufferByTopic(self, current_summary: str, dialogue_turns: str) -> int:
        """
        判断对话是否延续已有话题，返回延续轮次数量
        0表示没有延续，全部是新话题
        >0 表示延续的轮次数量
        """
        data = self.llm_management.generate(
            prompt_name="split_buffer_by_topic_continuation",
            options={"temperature": 0, "top_p": 1},
            current_summary=current_summary,
            dialogue_turns=dialogue_turns
        )
        logger.debug(f"Split Buffer By Topic Response: {data}")
        return data.get("index", 0)
    

    def judgeDialogueSummary(
            self,
            summary: str,
            dialogues: str
        ) -> dict:
            """
            判断是否需要对最近对话进行摘要
            返回格式：
            {
              "need_summary": true | false
            }
            """

            # === 1. 构造输入文本（一定要短） ===
            data = self.llm_management.generate(
                prompt_name="judge_dialogue_summary",
                options={"temperature": 0, "top_p": 1},
                summary=summary,
                dialogues=dialogues
            )

            logger.debug(f"Judge Dialogue Summary Response: {data}")
            if data is None:
                return {"need_summary": False}
            else:
                return data