"""Unit test: Bellman-Ford algorithm."""
import pytest
from src.core.graph import Graph
from src.core.algorithms.bellman_ford import BellmanFordAlgorithm, NegativeCycleError


def test_bellman_ford_negative_weights():
    """Test Bellman-Ford on graph with negative weights."""
    graph = Graph.from_edge_list([
        ("A", "B", 5),
        ("A", "C", 2),
        ("C", "D", 1),
        ("D", "F", -3),
        ("F", "B", 1)
    ])
    
    algorithm = BellmanFordAlgorithm()
    path, cost = algorithm.compute(graph, "A", "B")
    
    assert path == ["A", "C", "D", "F", "B"]
    assert cost == pytest.approx(1.0)


def test_bellman_ford_detects_negative_cycle():
    """Test that Bellman-Ford detects negative cycles."""
    graph = Graph.from_edge_list([
        ("A", "B", 1),
        ("B", "C", 1),
        ("C", "A", -3)
    ])
    
    algorithm = BellmanFordAlgorithm()
    
    with pytest.raises(NegativeCycleError) as exc_info:
        algorithm.compute(graph, "A", "B")
    
    assert exc_info.value.cycle is not None
    # Cycle cost calculation may vary based on implementation
    assert exc_info.value.cycle_cost <= 0  # Should be non-positive


def test_bellman_ford_positive_weights():
    """Test Bellman-Ford works on positive-weight graphs (slower than Dijkstra)."""
    graph = Graph.from_edge_list([
        ("A", "B", 5),
        ("A", "C", 2),
        ("C", "B", 1)
    ])
    
    algorithm = BellmanFordAlgorithm()
    path, cost = algorithm.compute(graph, "A", "B")
    
    assert path == ["A", "C", "B"]
    assert cost == pytest.approx(3.0)


def test_bellman_ford_no_path():
    """Test Bellman-Ford when no path exists."""
    graph = Graph.from_edge_list([
        ("A", "B", 1),
        ("C", "D", 1)
    ])
    
    algorithm = BellmanFordAlgorithm()
    
    with pytest.raises(ValueError, match="No path"):
        algorithm.compute(graph, "A", "D")
