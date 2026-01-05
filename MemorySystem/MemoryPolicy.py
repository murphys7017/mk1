
from SystemPrompt import SystemPrompt
from MessageModel import ChatMessage, DialogueMessage
from loguru import logger
from LocalModelFunc import LocalModelFunc
from tools import tools
class MemoryPolicy:
    """Memory policy for managing memory storage and retrieval.
    输入应为 对话的文本形式 话题的文本
    """

    def __init__(self, local_model_func: LocalModelFunc):
         self.local_model_func = local_model_func
    
    def splitBufferByTopic(self, current_summary: str, dialogue_turns: str) -> int:
        """
        判断对话是否延续已有话题，返回延续轮次数量
        0表示没有延续，全部是新话题
        >0 表示延续的轮次数量
        """
        input_text = SystemPrompt.split_buffer_by_topic_continuation_prompt().format(
            current_summary=current_summary,
            dialogue_turns=dialogue_turns
        )
        input_text = tools.normalizeBlock(input_text)
        model = SystemPrompt.split_buffer_by_topic_continuation_model()
        options = {"temperature": 0, "top_p": 1}
        # data = self._call_openai_api(input_text, model, options)
        data = self.local_model_func._call_ollama_api(input_text, model, options)
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

            input_text = f"""

    【已有摘要】
    {summary if summary else "（无）"}

    【最近对话】
    {dialogues}
    """
            input_text = SystemPrompt.judge_dialogue_summary_prompt() + input_text
            input_text = tools.normalizeBlock(input_text)
            # === 2. 调用 Ollama（示意） ===
            model = SystemPrompt.judge_dialogue_summary_model()
            options = {"temperature": 0, "top_p": 1}

            data = self.local_model_func._call_ollama_api(input_text, model, options)
            logger.debug(f"Judge Dialogue Summary Response: {data}")
            if data is None:
                return {"need_summary": False}
            else:
                return data