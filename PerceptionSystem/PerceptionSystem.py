import time
from typing import Any
from LLM.LLMManagement import LLMManagement
from DataClass.ChatMessage import ChatMessage
from PerceptionSystem.LtpAnalyze import LtpAnalyze
from PerceptionSystem.OllamaAnalyze import OllamaAnalyze
import asyncio
from loguru import logger


class PerceptionSystem:
    def __init__(self, llm_management: LLMManagement):
        self.llm_management = llm_management

        self.analyzers = {
            "text": [OllamaAnalyze(self.llm_management), LtpAnalyze()]
        }

    async def analyze(
        self,
        input_data: dict[str, Any],
        timeout: float = 5.0
    ) -> ChatMessage:
        """
        并发分析多种媒体类型，整体受 timeout 限制。
        input_data 示例: {"text": "hello", "image": "base64_or_path", "audio": "..."}
        """
        logger.debug(f"PerceptionSystem.analyze input_data: {input_data}")
        tasks = []
        loop = asyncio.get_running_loop()
        message = ChatMessage(
            role="user",
            content="",
            timestamp=int(time.time() * 1000),
            timedate=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            extra={}
        )
        message.video = input_data.get("video", None)
        message.voice = input_data.get("audio", None)
        message.image = input_data.get("image", None)
        message.content = input_data.get("text", "")

        # 为每个媒体类型启动对应的分析器 多线程同时执行 控制启动数量 important
        for media_type, content in input_data.items():
            if media_type in self.analyzers:
                analyzers = self.analyzers.get(media_type, [])
                for analyzer in analyzers:
                    # 将同步 analyze 包装为异步（使用线程池）
                    task = loop.run_in_executor(
                        None,
                        analyzer.analyze,
                        content
                    )
                    tasks.append(task)

        if not tasks:
            return message

        
        done, pending = await asyncio.wait(tasks, timeout=timeout)
        logger.debug(
            f"PerceptionSystem.analyze wait finished. timeout={timeout}, "
            f"done={len(done)}, pending={len(pending)}"
        )
        for task in pending:
            task.cancel()
        
        results = []
        for t in done:
            try:
                # done 的 future 不需要 await，用 result() 更直观
                results.append(t.result())
                for key, value in t.result().items():
                    if message.extra is None:
                        message.extra = {}
                    message.extra[key] = value
            except Exception as e:
                logger.exception(f"Analyzer task failed: {e}")

        logger.debug(f"PerceptionSystem.analyze results: {results}")
        return message


