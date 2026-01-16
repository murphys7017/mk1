import os
import sys
import logging
from loguru import logger

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
