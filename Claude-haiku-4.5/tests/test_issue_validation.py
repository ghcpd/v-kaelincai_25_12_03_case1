"""
Validation Tests - Ensure v2 fixes the original issue_project bugs

These tests validate that the routing_v2 implementation fixes:
1. Dijkstra incorrectly handling negative weights
2. Premature visited marking causing suboptimal paths
3. Missing validation leading to crashes

Run with: pytest -v tests/test_issue_validation.py --tb=short
"""

import pytest
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from routing_v2 import RoutingService, RoutingConfig, Graph


@pytest.fixture
def routing_service():
    """Create a routing service for validation tests."""
    config = RoutingConfig(
        timeout_ms=1000,
        algorithm_hint="auto",
        cache_enabled=True,
        cache_ttl_sec=300
    )
    return RoutingService(config)


@pytest.fixture
def negative_weight_graph():
    """Load the original negative-weight test graph."""
    # This graph has:
    # A -> B: weight=5
    # A -> C: weight=2
    # C -> D: weight=1
    # D -> F: weight=-3
    # F -> B: weight=1
    # This creates a path A->C->D->F->B with cost=1 (via negative edge)
    edges = [
        {"source": "A", "target": "B", "weight": 5},
        {"source": "A", "target": "C", "weight": 2},
        {"source": "C", "target": "D", "weight": 1},
        {"source": "D", "target": "F", "weight": -3},
        {"source": "F", "target": "B", "weight": 1},
        {"source": "A", "target": "E", "weight": 1},
        {"source": "E", "target": "B", "weight": 6}
    ]
    return Graph(edges=edges)


class TestOriginalIssueV1:
    """Validate that v2 fixes the original negative-weight bug."""
    
    def test_v2_detects_negative_weights_and_uses_bellman_ford(self, routing_service, negative_weight_graph):
        """Test that v2 automatically detects negative weights and switches to Bellman-Ford."""
        result = routing_service.compute_shortest_path(
            negative_weight_graph,
            "A",
            "B",
            request_id="issue_validation_001"
        )
        
        # Should succeed (unlike v1)
        assert result.status == "success", f"v2 should handle negative weights, got: {result.error_message}"
        assert result.algorithm == "bellman_ford", "v2 should use Bellman-Ford for negative weights"
    
    def test_v2_finds_optimal_path_with_negative_edge(self, routing_service, negative_weight_graph):
        """Test that v2 finds the optimal path through the negative edge."""
        result = routing_service.compute_shortest_path(
            negative_weight_graph,
            "A",
            "B",
            request_id="issue_validation_002"
        )
        
        # Should find the optimal path: A -> C -> D -> F -> B with cost=1
        assert result.status == "success"
        assert result.path == ["A", "C", "D", "F", "B"], f"Expected optimal path, got {result.path}"
        assert abs(result.cost - 1.0) < 1e-6, f"Expected cost=1.0, got {result.cost}"
    
    def test_v2_does_not_use_suboptimal_direct_edge(self, routing_service, negative_weight_graph):
        """Test that v2 doesn't use the suboptimal A->B direct edge (cost=5)."""
        result = routing_service.compute_shortest_path(
            negative_weight_graph,
            "A",
            "B",
            request_id="issue_validation_003"
        )
        
        # Cost should be 1.0, NOT 5.0 (the direct edge cost)
        assert result.cost < 5.0, f"v2 should find better path than direct edge; got cost={result.cost}"
        assert abs(result.cost - 1.0) < 1e-6, f"Expected optimal cost=1.0, got {result.cost}"
        assert "B" not in result.path[:-1], "Path should not use direct A->B edge"


class TestNegativeCyclePrevention:
    """Validate that v2 prevents negative cycle infinite loops."""
    
    def test_v2_detects_negative_cycle(self, routing_service):
        """Test that v2 detects and rejects negative cycles."""
        # Create a simple negative cycle: A -> B -> C -> A (all weight=-1)
        edges = [
            {"source": "A", "target": "B", "weight": -1},
            {"source": "B", "target": "C", "weight": -1},
            {"source": "C", "target": "A", "weight": -1}
        ]
        graph = Graph(edges=edges)
        
        result = routing_service.compute_shortest_path(
            graph,
            "A",
            "C",
            request_id="cycle_validation_001"
        )
        
        # Should detect cycle and return error
        assert result.status == "error", f"v2 should detect negative cycle, got status={result.status}"
        assert result.error_code == "NEG_CYCLE", f"Expected NEG_CYCLE error, got {result.error_code}"
        assert result.path is None, "Cycle should have no valid path"


class TestEdgeCaseHandling:
    """Validate that v2 handles edge cases that v1 crashed on."""
    
    def test_v2_handles_empty_graph(self, routing_service):
        """Test that v2 gracefully handles empty graph."""
        edges = []
        graph = Graph(edges=edges)
        
        result = routing_service.compute_shortest_path(
            graph,
            "A",
            "B",
            request_id="edge_case_001"
        )
        
        # Should return error, not crash
        assert result.status == "error"
        assert result.error_code == "EMPTY_GRAPH"
    
    def test_v2_handles_missing_node(self, routing_service):
        """Test that v2 gracefully handles missing node."""
        edges = [
            {"source": "A", "target": "B", "weight": 1}
        ]
        graph = Graph(edges=edges)
        
        result = routing_service.compute_shortest_path(
            graph,
            "X",  # Non-existent node
            "B",
            request_id="edge_case_002"
        )
        
        # Should return error, not crash
        assert result.status == "error"
        assert result.error_code == "NODE_NOT_FOUND"
    
    def test_v2_handles_unreachable_goal(self, routing_service):
        """Test that v2 gracefully handles unreachable goal."""
        edges = [
            {"source": "A", "target": "B", "weight": 1},
            {"source": "C", "target": "D", "weight": 1}
        ]
        graph = Graph(edges=edges)
        
        result = routing_service.compute_shortest_path(
            graph,
            "A",
            "D",  # Unreachable from A
            request_id="edge_case_003"
        )
        
        # Should return error, not crash
        assert result.status == "error"
        assert result.error_code == "NO_PATH_FOUND"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
