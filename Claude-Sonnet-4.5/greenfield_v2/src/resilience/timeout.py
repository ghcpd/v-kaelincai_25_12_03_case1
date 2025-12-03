"""Timeout context manager."""
import signal
import logging
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when operation exceeds timeout."""
    pass


@contextmanager
def timeout(seconds: float, operation: Optional[str] = None):
    """
    Context manager for enforcing timeouts.
    
    Note: On Windows, uses threading instead of signals.
    
    Args:
        seconds: Timeout in seconds
        operation: Operation name for logging
        
    Raises:
        TimeoutError: If operation exceeds timeout
        
    Example:
        with timeout(5.0, "graph_loading"):
            graph = load_graph(path)
    """
    import platform
    
    if platform.system() == "Windows":
        # Windows doesn't support signal.alarm, use threading
        import threading
        
        def timeout_handler():
            raise TimeoutError(f"Operation exceeded {seconds}s timeout")
        
        timer = threading.Timer(seconds, timeout_handler)
        timer.start()
        
        try:
            yield
        except TimeoutError:
            op_name = operation or "operation"
            logger.error(f"Timeout: {op_name} exceeded {seconds}s")
            raise
        finally:
            timer.cancel()
    else:
        # Unix-like systems can use signals
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Operation exceeded {seconds}s timeout")
        
        # Set signal handler
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, seconds)
        
        try:
            yield
        except TimeoutError:
            op_name = operation or "operation"
            logger.error(f"Timeout: {op_name} exceeded {seconds}s")
            raise
        finally:
            # Restore old handler and cancel alarm
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
