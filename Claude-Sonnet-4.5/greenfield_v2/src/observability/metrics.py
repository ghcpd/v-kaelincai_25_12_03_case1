"""Prometheus metrics."""
from prometheus_client import Counter, Histogram, Gauge, Enum


# Request counters
requests_total = Counter(
    "routing_requests_total",
    "Total routing requests",
    ["graph_id", "algorithm"]
)

success_total = Counter(
    "routing_success_total",
    "Successful routing requests",
    ["graph_id", "algorithm"]
)

error_total = Counter(
    "routing_error_total",
    "Failed routing requests",
    ["graph_id", "error_type"]
)

# Cache metrics
cache_hit_total = Counter(
    "routing_cache_hit_total",
    "Cache hits",
    ["graph_id"]
)

cache_miss_total = Counter(
    "routing_cache_miss_total",
    "Cache misses",
    ["graph_id"]
)

# Retry metrics
retry_total = Counter(
    "routing_retry_total",
    "Retry attempts",
    ["operation"]
)

# Timeout metrics
timeout_total = Counter(
    "routing_timeout_total",
    "Timeout occurrences",
    ["operation"]
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    "routing_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service"]
)

# Latency histogram
latency_ms = Histogram(
    "routing_latency_ms",
    "Request latency in milliseconds",
    ["graph_id", "algorithm"],
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
)

# Algorithm selection
algorithm_selection_total = Counter(
    "routing_algorithm_selection_total",
    "Algorithm selection count",
    ["algorithm", "reason"]
)

# Validation errors
validation_error_total = Counter(
    "routing_validation_error_total",
    "Validation errors",
    ["reason"]
)
