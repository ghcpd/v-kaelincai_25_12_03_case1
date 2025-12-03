"""Integration test: Healthy path (positive weights)."""
import pytest
from src.routing import RoutingEngine, RouteRequest
from src.core.graph import Graph


def test_healthy_path_positive_weights():
    """
    TC7: Healthy Path (Positive Weights)
    
    Verifies baseline correctness for common case with all positive weights.
    """
    engine = RoutingEngine(
        graph_loader_func=lambda gid: _load_test_graph("positive_weight")
    )
    
    request = RouteRequest(
        request_id="test-healthy-007",
        graph_id="positive_weight",
        start_node="A",
        goal_node="B",
        algorithm_hint="auto"
    )
    
    response = engine.compute_route(request)
    
    # Should succeed
    assert response.status == "success"
    assert response.path == ["A", "C", "D", "B"]
    assert response.cost == pytest.approx(4.0)
    
    # Should use Dijkstra
    assert response.metadata["algorithm_used"] == "dijkstra"
    
    # Should be fast
    assert response.metadata["computation_time_ms"] < 50


def test_direct_path_vs_shortest():
    """Verify algorithm finds shortest path, not direct path."""
    engine = RoutingEngine(
        graph_loader_func=lambda gid: _load_test_graph("positive_weight")
    )
    
    request = RouteRequest(
        request_id="test-shortest",
        graph_id="positive_weight",
        start_node="A",
        goal_node="B"
    )
    
    response = engine.compute_route(request)
    
    # Should find A->C->D->B (cost 4), not A->B (cost 5)
    assert response.path == ["A", "C", "D", "B"]
    assert response.cost < 5.0


def _load_test_graph(graph_name: str) -> Graph:
    """Helper to load test graph."""
    return Graph.from_json_file(f"data/{graph_name}.json")
