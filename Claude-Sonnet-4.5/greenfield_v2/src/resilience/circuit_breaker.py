"""Circuit breaker pattern implementation."""
import time
import logging
from enum import Enum
from typing import Callable, Optional
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = 0      # Normal operation
    OPEN = 1        # Failing fast
    HALF_OPEN = 2   # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Fast fail, requests rejected immediately
    - HALF_OPEN: Test mode, single request allowed to test recovery
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_duration: float = 60.0,
        expected_exceptions: tuple = (Exception,)
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening
            timeout_duration: Seconds to stay open before half-open
            expected_exceptions: Exceptions that count as failures
        """
        self.failure_threshold = failure_threshold
        self.timeout_duration = timeout_duration
        self.expected_exceptions = expected_exceptions
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs):
        """
        Call function with circuit breaker protection.
        
        Raises:
            Exception: Original exception if circuit is closed/half-open
            CircuitBreakerOpenError: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker half-open, testing recovery")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker open, will retry after "
                    f"{self.timeout_duration - (time.time() - self.last_failure_time):.1f}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.timeout_duration
        )
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker closed after successful test")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker re-opened after failed test")
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker opened after {self.failure_count} failures"
            )
            self.state = CircuitState.OPEN
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator syntax support."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass
