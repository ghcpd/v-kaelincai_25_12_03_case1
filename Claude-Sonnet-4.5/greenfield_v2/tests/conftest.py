"""Pytest configuration and shared fixtures."""
import pytest
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture
def sample_positive_graph():
    """Fixture for positive weight graph."""
    from src.core.graph import Graph
    return Graph.from_json_file("data/positive_weight.json")


@pytest.fixture
def sample_negative_graph():
    """Fixture for negative weight graph."""
    from src.core.graph import Graph
    return Graph.from_json_file("data/negative_weight.json")


@pytest.fixture
def sample_cycle_graph():
    """Fixture for negative cycle graph."""
    from src.core.graph import Graph
    return Graph.from_json_file("data/negative_cycle.json")
