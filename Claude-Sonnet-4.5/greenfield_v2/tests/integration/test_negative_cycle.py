"""Integration test: Negative cycle detection."""
import pytest
from src.routing import RoutingEngine, RouteRequest
from src.core.graph import Graph
from src.core.algorithms import BellmanFordAlgorithm, NegativeCycleError


def test_negative_cycle_detection():
    """
    TC6: Negative Cycle Detection
    
    Verifies that v2 detects and rejects graphs with negative cycles.
    """
    engine = RoutingEngine(
        graph_loader_func=lambda gid: _load_test_graph("negative_cycle")
    )
    
    request = RouteRequest(
        request_id="test-cycle-006",
        graph_id="negative_cycle",
        start_node="A",
        goal_node="B",
        algorithm_hint="auto"
    )
    
    response = engine.compute_route(request)
    
    # Should return error
    assert response.status == "error"
    assert response.error["code"] == "NEGATIVE_CYCLE_DETECTED"
    assert "cycle" in response.error["message"].lower()
    
    # Should include cycle details
    assert "cycle" in response.error["details"]
    assert "cycle_cost" in response.error["details"]


def test_bellman_ford_cycle_detection_direct():
    """Verify Bellman-Ford directly raises NegativeCycleError."""
    graph = _load_test_graph("negative_cycle")
    algorithm = BellmanFordAlgorithm()
    
    with pytest.raises(NegativeCycleError) as exc_info:
        algorithm.compute(graph, "A", "B")
    
    # Check exception contains cycle info
    assert exc_info.value.cycle is not None
    assert exc_info.value.cycle_cost <= 0


def _load_test_graph(graph_name: str) -> Graph:
    """Helper to load test graph."""
    return Graph.from_json_file(f"data/{graph_name}.json")
