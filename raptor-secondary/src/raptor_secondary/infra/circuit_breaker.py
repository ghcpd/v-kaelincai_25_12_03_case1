from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional


@dataclass
class CircuitBreakerState:
    failures: int = 0
    opened_at: Optional[float] = None


class CircuitBreaker:
    def __init__(self, failure_threshold: int, reset_timeout_seconds: float) -> None:
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        self.state = CircuitBreakerState()

    def allow_request(self) -> bool:
        if self.state.opened_at is None:
            return True
        elapsed = time.time() - self.state.opened_at
        if elapsed >= self.reset_timeout_seconds:
            # half-open: allow one request
            return True
        return False

    def on_success(self) -> None:
        self.state.failures = 0
        self.state.opened_at = None

    def on_failure(self) -> None:
        self.state.failures += 1
        if self.state.failures >= self.failure_threshold:
            self.state.opened_at = time.time()

    @property
    def is_open(self) -> bool:
        if self.state.opened_at is None:
            return False
        elapsed = time.time() - self.state.opened_at
        if elapsed >= self.reset_timeout_seconds:
            # allow retry
            return False
        return True
