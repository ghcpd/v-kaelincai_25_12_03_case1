from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_initial_seconds: float = 0.05
    backoff_factor: float = 2.0
    backoff_max_seconds: float = 1.0


@dataclass
class TimeoutConfig:
    schedule_timeout_seconds: float = 0.5
    cancel_timeout_seconds: float = 0.5


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 2
    reset_timeout_seconds: float = 1.0


@dataclass
class AppConfig:
    retry: RetryConfig = field(default_factory=RetryConfig)
    timeout: TimeoutConfig = field(default_factory=TimeoutConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)


DEFAULT_CONFIG = AppConfig()
