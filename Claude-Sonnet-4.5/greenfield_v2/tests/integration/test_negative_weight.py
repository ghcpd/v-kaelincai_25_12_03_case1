"""Integration test: Negative weight handling."""
import pytest
from src.routing import RoutingEngine, RouteRequest
from src.core.graph import Graph


def test_negative_weight_correct_path():
    """
    TC5: Negative Weight Handling (Correctness)
    
    Verifies that v2 correctly computes shortest path for graphs
    with negative weights using Bellman-Ford algorithm.
    """
    engine = RoutingEngine(
        graph_loader_func=lambda gid: _load_test_graph("negative_weight")
    )
    
    request = RouteRequest(
        request_id="test-negative-005",
        graph_id="negative_weight",
        start_node="A",
        goal_node="B",
        algorithm_hint="auto"
    )
    
    response = engine.compute_route(request)
    
    # Should succeed with correct path
    assert response.status == "success"
    assert response.path == ["A", "C", "D", "F", "B"]
    assert response.cost == pytest.approx(1.0)
    
    # Should use Bellman-Ford
    assert response.metadata["algorithm_used"] == "bellman_ford"
    
    # Should complete quickly
    assert response.metadata["computation_time_ms"] < 100


def test_negative_weight_algorithm_selection():
    """Verify automatic algorithm selection for negative weights."""
    from src.core.algorithms import AlgorithmSelector
    
    graph = _load_test_graph("negative_weight")
    
    # Auto selection should choose Bellman-Ford
    algorithm = AlgorithmSelector.select(graph, "auto")
    assert algorithm.name() == "bellman_ford"


def test_dijkstra_rejects_negative_weights():
    """Verify Dijkstra explicitly rejects negative weights."""
    from src.core.algorithms import DijkstraAlgorithm
    
    graph = _load_test_graph("negative_weight")
    algorithm = DijkstraAlgorithm()
    
    with pytest.raises(ValueError, match="non-negative"):
        algorithm.compute(graph, "A", "B")


def _load_test_graph(graph_name: str) -> Graph:
    """Helper to load test graph."""
    return Graph.from_json_file(f"data/{graph_name}.json")
