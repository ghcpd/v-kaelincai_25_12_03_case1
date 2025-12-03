"""Integration test: Idempotency."""
import pytest
import time
from src.routing import RoutingEngine, RouteRequest


def test_idempotency_duplicate_requests(tmp_path):
    """
    TC1: Idempotency - Duplicate Requests
    
    Verifies that duplicate requests with same request_id return
    identical cached results without recomputation.
    """
    # Setup
    engine = RoutingEngine(
        graph_loader_func=lambda gid: _load_test_graph("positive_weight")
    )
    
    request = RouteRequest(
        request_id="test-idempotency-001",
        graph_id="positive_weight",
        start_node="A",
        goal_node="B",
        algorithm_hint="auto"
    )
    
    # First request - should compute
    response1 = engine.compute_route(request)
    
    assert response1.status == "success"
    assert response1.path == ["A", "C", "D", "B"]
    assert response1.cost == 4.0
    assert response1.metadata["cache_hit"] is False
    time1 = response1.metadata["computation_time_ms"]
    
    # Second request - should be cached
    response2 = engine.compute_route(request)
    
    assert response2.status == "success"
    assert response2.path == ["A", "C", "D", "B"]
    assert response2.cost == 4.0
    assert response2.metadata["cache_hit"] is True
    
    # Cache hit should be much faster
    assert response2.metadata["computation_time_ms"] < time1 * 0.1 or \
           response2.metadata["computation_time_ms"] < 5  # < 5ms for cache


def test_idempotency_different_requests():
    """Verify different request_ids are not cached together."""
    engine = RoutingEngine(
        graph_loader_func=lambda gid: _load_test_graph("positive_weight")
    )
    
    request1 = RouteRequest(
        request_id="test-001",
        graph_id="positive_weight",
        start_node="A",
        goal_node="B"
    )
    
    request2 = RouteRequest(
        request_id="test-002",
        graph_id="positive_weight",
        start_node="A",
        goal_node="B"
    )
    
    response1 = engine.compute_route(request1)
    response2 = engine.compute_route(request2)
    
    # Both should compute (no cache hit)
    assert response1.metadata["cache_hit"] is False
    assert response2.metadata["cache_hit"] is False


def _load_test_graph(graph_name: str):
    """Helper to load test graph."""
    from src.core.graph import Graph
    return Graph.from_json_file(f"data/{graph_name}.json")
