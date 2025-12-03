"""Unit test: Result validator."""
import pytest
from src.core.graph import Graph
from src.core.validator import ResultValidator, ValidationError


def test_validator_valid_path():
    """Test validator accepts valid path."""
    graph = Graph.from_edge_list([
        ("A", "B", 5),
        ("A", "C", 2),
        ("C", "B", 1)
    ])
    
    path = ["A", "C", "B"]
    cost = 3.0
    
    # Should not raise
    ResultValidator.validate_path(graph, path, cost)


def test_validator_invalid_edge():
    """Test validator rejects path with non-existent edge."""
    graph = Graph.from_edge_list([
        ("A", "B", 5),
        ("A", "C", 2)
    ])
    
    path = ["A", "C", "D"]  # C->D doesn't exist
    cost = 10.0
    
    with pytest.raises(ValidationError, match="does not exist"):
        ResultValidator.validate_path(graph, path, cost)


def test_validator_cost_mismatch():
    """Test validator rejects incorrect cost."""
    graph = Graph.from_edge_list([
        ("A", "B", 5),
        ("A", "C", 2),
        ("C", "B", 1)
    ])
    
    path = ["A", "C", "B"]
    cost = 10.0  # Wrong cost (should be 3.0)
    
    with pytest.raises(ValidationError, match="Cost mismatch"):
        ResultValidator.validate_path(graph, path, cost)


def test_validator_single_node_path():
    """Test validator rejects single-node path."""
    graph = Graph.from_edge_list([
        ("A", "B", 5)
    ])
    
    path = ["A"]
    cost = 0.0
    
    with pytest.raises(ValidationError, match="at least 2 nodes"):
        ResultValidator.validate_path(graph, path, cost)
