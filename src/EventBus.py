import asyncio
import time
from typing import Any, Callable

from loguru import logger

from DataClass.ChatEvent import ChatEvent


class EventBus:
    """
    Lightweight in-process event bus. It only dispatches events to subscribers.
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable[[ChatEvent], Any]]] = {}
        self._queue: asyncio.Queue[ChatEvent] = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    def subscribe(self, event_type: str, handler: Callable[[ChatEvent], Any]):
        # 按事件类型注册处理器
        handlers = self._handlers.setdefault(event_type, [])
        handlers.append(handler)

    def publish(self, event_type: str, data: Any, turn_id: int | None = None):
        # 只负责发布事件，异步分发给订阅者
        event = ChatEvent(
            event_type=event_type,
            turn_id=turn_id if turn_id is not None else -1,
            timestamp=int(time.time() * 1000),
            data=data
        )

        try:
            self._ensure_worker()
            self._queue.put_nowait(event)
        except RuntimeError:
            self._dispatch_sync(event)

    def _ensure_worker(self):
        # 确保后台消费协程已启动
        if self._worker_task is None or self._worker_task.done():
            loop = asyncio.get_running_loop()
            self._worker_task = loop.create_task(self._run())

    def _dispatch_sync(self, event: ChatEvent):
        # 同步环境下直接派发（用于没有事件循环时）
        for handler in self._handlers.get(event.event_type, []):
            try:
                result = handler(event)
                if asyncio.iscoroutine(result):
                    asyncio.run(result)
            except Exception as exc:
                logger.exception(f"Event handler failed: {exc}")

    async def _run(self):
        # 队列消费者：持续拉取事件并派发
        while True:
            event = await self._queue.get()
            await self._dispatch(event)
            self._queue.task_done()

    async def _dispatch(self, event: ChatEvent):
        # 分发给所有订阅者，支持 sync/async 处理器
        handlers = self._handlers.get(event.event_type, [])
        if not handlers:
            return

        loop = asyncio.get_running_loop()
        tasks = []
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(asyncio.create_task(handler(event)))
                else:
                    tasks.append(loop.run_in_executor(None, handler, event))
            except Exception as exc:
                logger.exception(f"Event handler setup failed: {exc}")

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.exception(f"Event handler failed: {result}")
