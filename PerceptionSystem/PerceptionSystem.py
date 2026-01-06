import time
from typing import Any
from LLM.LLMManagement import LLMManagement
from DataClass.ChatMessage import ChatMessage
from PerceptionSystem.TextAnalyze import TextAnalyze
import asyncio
from loguru import logger


class PerceptionSystem:
    def __init__(self, llm_management: LLMManagement):
        self.llm_management = llm_management

        self.analyzers = {
            "text": TextAnalyze(self.llm_management)
        }

    async def analyze(
        self,
        input_data: dict[str, Any],
        timeout: float = 5.0
    ) -> list[ChatMessage]:
        """
        并发分析多种媒体类型，整体受 timeout 限制。
        input_data 示例: {"text": "hello", "image": "base64_or_path", "audio": "..."}
        """
        tasks = []
        loop = asyncio.get_running_loop()

        # 为每种存在的媒体类型创建异步任务
        for media_type, content in input_data.items():
            if media_type in self.analyzers:
                analyzer = self.analyzers.get(media_type, None)
                if analyzer is None:
                    continue
                # 将同步 analyze 包装为异步（使用线程池）
                task = loop.run_in_executor(
                    None,
                    analyzer.analyze,
                    content
                )
                tasks.append(task)

        if not tasks:
            return []

        
        done, pending = await asyncio.wait(tasks, timeout=timeout)
        for task in pending:
                task.cancel()
        results = [await t for t in done if not t.exception()]
        return results


