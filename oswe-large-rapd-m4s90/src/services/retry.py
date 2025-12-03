from __future__ import annotations

import time
from typing import Callable, Type, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout


def with_retry(func: Callable[[], Any], retries: int = 3, backoff: float = 0.1, exceptions: Tuple[Type[BaseException], ...] = (Exception,), timeout: float | None = None):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            if timeout is None:
                return func()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func)
                return future.result(timeout=timeout)
        except FuturesTimeout as exc:
            last_exc = exc
        except exceptions as exc:
            last_exc = exc
        time.sleep(backoff * (2 ** attempt))
    if last_exc:
        raise last_exc
