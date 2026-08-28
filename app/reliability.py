import asyncio
import inspect
import json
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

T = TypeVar("T")
logger = logging.getLogger("rag_assistant")


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def log_event(event: str, **fields: Any) -> None:
    logger.info(json.dumps({"event": event, **fields}, sort_keys=True))


async def retry_async(operation: Callable[[], Awaitable[T]], attempts: int = 3, base_delay: float = 0.5, max_delay: float = 8.0) -> T:
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception:
            if attempt == attempts - 1:
                raise
            delay = min(max_delay, base_delay * (2**attempt))
            log_event("retry", attempt=attempt + 1, delay_seconds=delay)
            await asyncio.sleep(delay)
    raise RuntimeError("retry operation did not execute")


class Timer:
    def __init__(self) -> None:
        self.started = time.perf_counter()

    @property
    def elapsed_ms(self) -> float:
        return round((time.perf_counter() - self.started) * 1000, 2)


