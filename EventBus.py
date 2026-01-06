import asyncio
from typing import Callable


class EventBus:
    def __init__(self):
        self._handlers = {}
        self._queue = asyncio.Queue()

    def subscribe(self, event_type: str, handler: Callable):
        """注册处理器"""
        pass
    
    def publish(self, event_type: str,  dict):
        """发布事件"""
        pass