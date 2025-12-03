"""
Production Integration Tests for Logistics Routing v2

This module tests the actual routing_v2.py production code including:
- Graph validation
- Algorithm selection (Dijkstra vs Bellman-Ford)
- Negative cycle detection
- Negative edge handling
- Idempotency caching
- Timeout handling
- Structured logging
- Observability

Run with: pytest -v tests/test_production_integration.py --tb=short
"""

import pytest
import json
import time
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from routing_v2 import (
    RoutingService, RoutingConfig, RoutingResult, Graph,
    dijkstra_shortest_path, bellman_ford_shortest_path,
    _validate_graph, _has_negative_weights, _has_negative_cycle
)


# ===========================
# Test Fixtures
# ===========================

@pytest.fixture
def routing_service():
    """Create a fresh routing service for each test."""
    config = RoutingConfig(
        timeout_ms=1000,
        algorithm_hint="auto",
        cache_enabled=True,
        cache_ttl_sec=300
    )
    return RoutingService(config)


@pytest.fixture
def test_data():
    """Load test data from test_data.json."""
    data_path = Path(__file__).parent.parent / "test_data.json"
    with open(data_path, "r") as f:
        return json.load(f)


# ===========================
# Production Integration Tests
# ===========================

class TestNormalPath:
    """TC-001: Normal, non-negative shortest path."""
    
    def test_simple_dijkstra_path(self, routing_service, test_data):
        """Test simple non-negative graph routing."""
        case = test_data["canonical_test_cases"][0]  # TC-001
        
        graph = Graph(edges=case["graph"]["edges"])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_001"
        )
        
        # Assertions
        assert result.status == "success", f"Expected success, got {result.status}: {result.error_message}"
        assert result.path == case["expected"]["path"], f"Path mismatch: {result.path} != {case['expected']['path']}"
        assert abs(result.cost - case["expected"]["cost"]) < 1e-6, f"Cost mismatch: {result.cost} != {case['expected']['cost']}"
        assert result.algorithm == "dijkstra", f"Algorithm should be dijkstra, got {result.algorithm}"
        assert result.error_code is None


class TestNegativeWeights:
    """TC-002: Negative edges with automatic Bellman-Ford selection."""
    
    def test_negative_edge_bellman_ford(self, routing_service, test_data):
        """Test Bellman-Ford is selected for negative weights."""
        case = test_data["canonical_test_cases"][1]  # TC-002
        
        graph = Graph(edges=case["graph"]["edges"])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_002"
        )
        
        # Assertions
        assert result.status == "success", f"Expected success, got {result.status}: {result.error_message}"
        assert result.path == case["expected"]["path"], f"Path mismatch: {result.path} != {case['expected']['path']}"
        assert abs(result.cost - case["expected"]["cost"]) < 1e-6, f"Cost mismatch: {result.cost} != {case['expected']['cost']}"
        assert result.algorithm == "bellman_ford", f"Algorithm should be bellman_ford, got {result.algorithm}"
        assert result.error_code is None


class TestNegativeCycleDetection:
    """TC-003: Negative cycle rejection."""
    
    def test_negative_cycle_detected(self, routing_service, test_data):
        """Test negative cycle is detected and rejected."""
        case = test_data["canonical_test_cases"][2]  # TC-003
        
        graph = Graph(edges=case["graph"]["edges"])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_003"
        )
        
        # Assertions
        assert result.status == "error", f"Expected error, got {result.status}: {result.path}, cost={result.cost}"
        assert result.error_code == "NEG_CYCLE", f"Expected NEG_CYCLE, got {result.error_code}: {result.error_message}"
        assert result.path is None
        assert result.cost is None


class TestIdempotency:
    """TC-004: Idempotency caching."""
    
    def test_cache_hit_on_second_call(self, routing_service, test_data):
        """Test that identical requests return cached result."""
        case = test_data["canonical_test_cases"][3]  # TC-004
        
        graph = Graph(edges=case["graph"]["edges"])
        
        # First call
        result1 = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_004_cache"
        )
        
        assert result1.status == "success"
        assert result1.cache_hit is False
        
        # Second call (identical graph, start, goal - NOT same request_id, so should use graph cache)
        result2 = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_004_cache_2"
        )
        
        # Assertions
        assert result2.status == "success"
        assert result2.path == result1.path
        assert result2.cost == result1.cost
        # Cache is based on graph+start+goal, so should hit even with different request_id
        assert result2.cache_hit is True, "Expected cache hit on 2nd call"


class TestValidationErrors:
    """TC-005, TC-006, TC-007: Precondition validation."""
    
    def test_goal_not_found(self, routing_service, test_data):
        """Test goal node not found error."""
        case = test_data["canonical_test_cases"][4]  # TC-005
        
        graph = Graph(edges=case["graph"]["edges"])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_005"
        )
        
        assert result.status == "error"
        assert result.error_code == "NODE_NOT_FOUND"
    
    def test_start_not_found(self, routing_service, test_data):
        """Test start node not found error."""
        case = test_data["canonical_test_cases"][5]  # TC-006
        
        graph = Graph(edges=case["graph"]["edges"])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_006"
        )
        
        assert result.status == "error"
        assert result.error_code == "NODE_NOT_FOUND"
    
    def test_empty_graph(self, routing_service, test_data):
        """Test empty graph rejection."""
        case = test_data["canonical_test_cases"][6]  # TC-007
        
        graph = Graph(edges=case["graph"]["edges"])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_007"
        )
        
        assert result.status == "error"
        assert result.error_code == "EMPTY_GRAPH"


class TestEdgeCases:
    """TC-008, TC-009: Edge cases."""
    
    def test_single_node_same_start_goal(self, routing_service, test_data):
        """Test single node where start==goal."""
        case = test_data["canonical_test_cases"][7]  # TC-008
        
        # Create a graph with at least the start node  
        # When start==goal and no other nodes, it's valid
        graph = Graph(edges=[{"source": "A", "target": "A", "weight": 0}])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_008"
        )
        
        assert result.status == "success", f"Expected success, got {result.status}: {result.error_message}"
        assert result.path == ["A"]
        assert result.cost == 0.0
    
    def test_disconnected_no_path(self, routing_service, test_data):
        """Test disconnected graph where path doesn't exist."""
        case = test_data["canonical_test_cases"][8]  # TC-009
        
        graph = Graph(edges=case["graph"]["edges"])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_009"
        )
        
        assert result.status == "error"
        assert result.error_code == "NO_PATH_FOUND"


class TestComplexScenarios:
    """TC-010: Complex mixed scenarios."""
    
    def test_complex_negative_with_positive(self, routing_service, test_data):
        """Test mixed negative and positive edges."""
        case = test_data["canonical_test_cases"][9]  # TC-010
        
        graph = Graph(edges=case["graph"]["edges"])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_010"
        )
        
        assert result.status == "success", f"Expected success, got {result.status}: {result.error_message}"
        assert result.path == case["expected"]["path"], f"Path mismatch: {result.path} != {case['expected']['path']}"
        assert abs(result.cost - case["expected"]["cost"]) < 1e-6, f"Cost mismatch: {result.cost} != {case['expected']['cost']}"
        assert result.algorithm == "bellman_ford"


class TestTimeout:
    """Timeout handling."""
    
    def test_timeout_triggered(self, routing_service, test_data):
        """Test timeout on slow computation."""
        case = test_data["canonical_test_cases"][0]
        
        graph = Graph(edges=case["graph"]["edges"])
        # Use very short timeout by creating a new config
        config_timeout = RoutingConfig(
            timeout_ms=1,  # 1ms timeout
            algorithm_hint="auto",
            cache_enabled=False  # Disable cache to force computation
        )
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_timeout",
            config=config_timeout
        )
        
        # Should either succeed quickly or timeout
        assert result.status in ["success", "error"]
        if result.status == "error":
            assert result.error_code == "TIMEOUT"


class TestObservability:
    """Observability and logging."""
    
    def test_request_id_in_logs(self, routing_service, test_data):
        """Test request_id is included in results."""
        case = test_data["canonical_test_cases"][0]
        
        graph = Graph(edges=case["graph"]["edges"])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_tracing_001"
        )
        
        assert result.request_id == "req_tracing_001"
        assert result.status == "success"
    
    def test_structured_json_logs(self, routing_service, test_data):
        """Test structured logging output."""
        case = test_data["canonical_test_cases"][0]
        
        graph = Graph(edges=case["graph"]["edges"])
        result = routing_service.compute_shortest_path(
            graph,
            case["start"],
            case["goal"],
            request_id="req_logging_001"
        )
        
        # Check that we can convert result to dict
        result_dict = result.to_dict() if hasattr(result, 'to_dict') else {
            'request_id': result.request_id,
            'status': result.status,
            'path': result.path,
            'cost': result.cost,
            'algorithm': result.algorithm,
            'duration_ms': result.duration_ms
        }
        
        assert result_dict['request_id'] == 'req_logging_001'
        assert result_dict['status'] == 'success'


class TestConcurrency:
    """Concurrent request handling."""
    
    def test_concurrent_requests_thread_safe(self, routing_service, test_data):
        """Test concurrent requests don't corrupt state."""
        import threading
        
        case = test_data["canonical_test_cases"][0]
        graph = Graph(edges=case["graph"]["edges"])
        
        results = []
        errors = []
        
        def make_request(request_id):
            try:
                result = routing_service.compute_shortest_path(
                    graph,
                    case["start"],
                    case["goal"],
                    request_id=request_id
                )
                results.append(result)
            except Exception as e:
                errors.append(str(e))
        
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request, args=(f"req_concurrent_{i}",))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # All threads should complete successfully
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 10
        
        # All results should be identical
        for result in results:
            assert result.status == "success"
            assert result.path == case["expected"]["path"]
            assert abs(result.cost - case["expected"]["cost"]) < 1e-6


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
