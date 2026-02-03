import os
import sys
import logging
from loguru import logger
import time
import inspect
from functools import wraps
from contextlib import contextmanager

# Centralized log configuration for the project
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = os.getenv("LOG_DIR", "logs")

os.makedirs(LOG_DIR, exist_ok=True)

# Remove default handlers added by loguru
logger.remove()

FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# Console sink
logger.add(sys.stderr, level=LOG_LEVEL, format=FORMAT, enqueue=True)

# File sink with rotation and retention
logger.add(
    os.path.join(LOG_DIR, "app.log"),
    level=LOG_LEVEL,
    rotation="10 MB",
    retention="10 days",
    compression="zip",
    format=FORMAT,
    enqueue=True,
)


class InterceptHandler(logging.Handler):
    """Intercept stdlib logging and route to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except Exception:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        # Walk back frames until we leave the logging module
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# Replace root handlers so stdlib logging goes through loguru
logging.basicConfig(handlers=[InterceptHandler()], level=LOG_LEVEL)

# Example: silence noisy library loggers or route them through intercept
for name in ("asyncio", "urllib3", "chardet"):
    logging.getLogger(name).handlers = [InterceptHandler()]

__all__ = ["logger"]


def _log_timing(name: str, elapsed_ms: float, level: str = "INFO"):
    try:
        logger.log(level.upper(), f"[timing] {name} took {elapsed_ms:.2f} ms")
    except Exception:
        logger.info(f"[timing] {name} took {elapsed_ms:.2f} ms")


def timeit_logger(name: str | None = None, level: str = "INFO"):
    """装饰器：记录函数执行时间并通过 loguru 输出。

    支持同步和异步函数。
    """
    def decorator(func):
        is_coro = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                _log_timing(name or f"{func.__module__}.{func.__qualname__}", elapsed, level)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - start) * 1000
                _log_timing(name or f"{func.__module__}.{func.__qualname__}", elapsed, level)

        return async_wrapper if is_coro else sync_wrapper

    return decorator


@contextmanager
def timing(name: str | None = None, level: str = "INFO"):
    """上下文管理器：记录代码块执行时间。

    用法：
        with timing("task.name"):
            do_work()
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000
        _log_timing(name or "block", elapsed, level)
