"""Unit test: Dijkstra algorithm."""
import pytest
from src.core.graph import Graph
from src.core.algorithms.dijkstra import DijkstraAlgorithm


def test_dijkstra_simple_path():
    """Test Dijkstra on simple positive-weight graph."""
    graph = Graph.from_edge_list([
        ("A", "B", 5),
        ("A", "C", 2),
        ("C", "B", 1)
    ])
    
    algorithm = DijkstraAlgorithm()
    path, cost = algorithm.compute(graph, "A", "B")
    
    assert path == ["A", "C", "B"]
    assert cost == pytest.approx(3.0)


def test_dijkstra_rejects_negative_weights():
    """Test that Dijkstra rejects negative weights."""
    graph = Graph.from_edge_list([
        ("A", "B", 5),
        ("A", "C", -2)
    ])
    
    algorithm = DijkstraAlgorithm()
    
    with pytest.raises(ValueError, match="non-negative"):
        algorithm.compute(graph, "A", "B")


def test_dijkstra_no_path():
    """Test Dijkstra when no path exists."""
    graph = Graph.from_edge_list([
        ("A", "B", 1),
        ("C", "D", 1)
    ])
    
    algorithm = DijkstraAlgorithm()
    
    with pytest.raises(ValueError, match="No path"):
        algorithm.compute(graph, "A", "D")


def test_dijkstra_self_loop():
    """Test Dijkstra with self-loop (should be ignored)."""
    graph = Graph.from_edge_list([
        ("A", "A", 0),
        ("A", "B", 5)
    ])
    
    algorithm = DijkstraAlgorithm()
    path, cost = algorithm.compute(graph, "A", "B")
    
    assert path == ["A", "B"]
    assert cost == pytest.approx(5.0)
