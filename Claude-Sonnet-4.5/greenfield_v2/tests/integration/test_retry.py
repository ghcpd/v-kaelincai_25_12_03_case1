"""Integration test: Retry with exponential backoff."""
import pytest
import time
from src.routing import RoutingEngine, RouteRequest
from src.core.graph import Graph


def test_retry_mechanism_transient_failure():
    """
    TC2: Retry with Exponential Backoff
    
    Verifies that transient failures are retried with exponential backoff.
    """
    attempt_count = 0
    
    def transient_failure_loader(graph_id: str) -> Graph:
        nonlocal attempt_count
        attempt_count += 1
        
        if attempt_count == 1:
            # First attempt fails
            raise IOError("Simulated transient I/O error")
        else:
            # Second attempt succeeds
            return Graph.from_json_file(f"data/{graph_id}.json")
    
    engine = RoutingEngine(graph_loader_func=transient_failure_loader)
    
    request = RouteRequest(
        request_id="test-retry-002",
        graph_id="positive_weight",
        start_node="A",
        goal_node="B"
    )
    
    start_time = time.time()
    response = engine.compute_route(request)
    elapsed = time.time() - start_time
    
    # Should eventually succeed
    assert response.status == "success"
    assert response.path == ["A", "C", "D", "B"]
    
    # Should have made 2 attempts
    assert attempt_count == 2
    
    # Should have waited for backoff (at least 1 second)
    assert elapsed >= 1.0


def test_retry_exhaustion():
    """Verify that retry gives up after max attempts."""
    attempt_count = 0
    
    def always_failing_loader(graph_id: str) -> Graph:
        nonlocal attempt_count
        attempt_count += 1
        raise IOError(f"Persistent failure (attempt {attempt_count})")
    
    engine = RoutingEngine(graph_loader_func=always_failing_loader)
    
    request = RouteRequest(
        request_id="test-retry-exhaustion",
        graph_id="positive_weight",
        start_node="A",
        goal_node="B"
    )
    
    response = engine.compute_route(request)
    
    # Should fail after max retries
    assert response.status == "error"
    
    # Should have attempted 3 times (initial + 2 retries)
    # Note: May be caught by circuit breaker, so check >= 3
    assert attempt_count >= 3 or response.error["code"] == "CIRCUIT_BREAKER_OPEN"
