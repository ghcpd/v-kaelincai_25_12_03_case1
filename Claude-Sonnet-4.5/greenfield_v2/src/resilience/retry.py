"""Retry decorator with exponential backoff."""
import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple

logger = logging.getLogger(__name__)


class TransientError(Exception):
    """Base class for transient errors that should be retried."""
    pass


def retry(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    backoff_multiplier: float = 2.0,
    max_wait: float = 10.0,
    exceptions: Tuple[Type[Exception], ...] = (TransientError,)
):
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        initial_wait: Initial wait time in seconds
        backoff_multiplier: Multiplier for exponential backoff
        max_wait: Maximum wait time in seconds
        exceptions: Tuple of exception types to retry on
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            wait_time = initial_wait
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"Max retries ({max_attempts}) reached for {func.__name__}: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {wait_time:.1f}s: {e}"
                    )
                    time.sleep(wait_time)
                    wait_time = min(wait_time * backoff_multiplier, max_wait)
            
            # Should never reach here
            raise RuntimeError("Retry logic error")
        
        return wrapper
    return decorator
