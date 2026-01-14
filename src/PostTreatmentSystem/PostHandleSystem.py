import time
from typing import Any
from DataClass.EventType import EventType
from EventBus import EventBus
from LLM.LLMManagement import LLMManagement
import asyncio
from loguru import logger

from PostTreatmentSystem.Live2d.Motion3Builder import Motion3Builder
from PostTreatmentSystem.LtpHandler import LtpHandler
from PostTreatmentSystem.OllamaHandler import OllamaHandler
from RawChatHistory.RawChatHistory import RawChatHistory


class PostHandleSystem:
    def __init__(self, 
                 event_bus: EventBus,
                 llm_management: LLMManagement, 
                  raw_history: RawChatHistory,
                 **kwargs):
        self.llm_management = llm_management
        self.raw_history = raw_history
        self.event_bus = event_bus

        self.handler_map = {
            0: [
                OllamaHandler(self.llm_management),  
                #LtpHandler(**kwargs)
                ],
            1: [ Motion3Builder(self.llm_management)]
        }

    async def handle(
        self,
        timeout: float = 20.0
    ):
        """
        并发分析多种媒体类型，整体受 timeout 限制。
        input_data 示例: {"text": "hello", "image": "base64_or_path", "audio": "..."}
        """
        logger.debug(f"PostHandleSystem.handle (sequential handlers)")
        loop = asyncio.get_running_loop()

        # 初始 summary 为空（传给第一步的 handlers）
        res = {}
        chat_history = []
        for chat in self.raw_history.getHistory(4):
            chat_history.append({"role": chat.role, "content": chat.content})
        
        res = {"chat_history": chat_history}

        # 顺序执行 handler_map 中按 key 排序的每一步（step）
        for step_idx in sorted(self.handler_map.keys()):
            handlers = self.handler_map.get(step_idx, [])
            step_results = []

            for handler in handlers:
                handler_fn = getattr(handler, "handler", None)
                if handler_fn is None:
                    logger.debug(f"Handler {handler} has no handler()")
                    continue

                # 同步 handler(raw_history, res) 放到线程池执行
                def call_handler_sync(h, raw_hist, res_dict):
                    try:
                        return h.handler(raw_hist, res_dict)
                    except Exception as e:
                        logger.exception(f"Handler {h} raised exception: {e}")
                        return None

                try:
                    fut = loop.run_in_executor(None, call_handler_sync, handler, self.raw_history, res)
                    out = await asyncio.wait_for(fut, timeout=timeout)
                except asyncio.TimeoutError:
                    logger.warning(f"Handler {handler} timed out in step {step_idx}")
                    out = None
                except Exception as e:
                    logger.exception(f"Handler {handler} failed: {e}")
                    out = None

                # handler 必须返回 dict（或 None），将返回结果合并入 res
                step_results.append(out)
                if isinstance(out, dict):
                    # 更新共享结果（覆盖同名字段）
                    res.update(out)

        self.event_bus.publish(
            event_type=EventType.POST_HANDLE_COMPLETED,
            data=res,
            turn_id=self.raw_history.getHistory(1)[-1].chat_turn_id
        )
        return res


