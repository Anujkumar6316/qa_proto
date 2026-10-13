"""Browser-session concurrency cap for the API.

Each crawl/execute/verify/report request can spin up a real browser session.
Without a cap, concurrent requests exhaust host memory/CPU. One bounded
semaphore per API process; routers acquire a slot via `with session_slot():`.
Size it with QA_BOT_MAX_CONCURRENT_SESSIONS (default 3).

Kept in its own module so routers can import it without creating an import
cycle through `bot.interfaces.api.__init__`.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager

logger = logging.getLogger("qa_bot.api")

_SEMAPHORE_LOCK = threading.Lock()
_session_semaphore: threading.Semaphore | None = None


def _get_session_semaphore() -> threading.Semaphore:
    global _session_semaphore
    if _session_semaphore is None:
        with _SEMAPHORE_LOCK:
            if _session_semaphore is None:
                from bot.settings import get_settings

                n = max(1, get_settings().MAX_CONCURRENT_SESSIONS)
                _session_semaphore = threading.Semaphore(n)
                logger.info("browser-session concurrency cap: %d", n)
    return _session_semaphore


@contextmanager
def session_slot():
    """Block until a browser-session slot is free, then run the body."""
    sem = _get_session_semaphore()
    sem.acquire()
    try:
        yield
    finally:
        sem.release()
