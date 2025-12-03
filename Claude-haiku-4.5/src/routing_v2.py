"""
Logistics Routing v2 – Production Implementation

Core modules:
- routing_v2.py: Unified shortest-path service with:
  * Graph validation & precondition checking
  * Algorithm selection (Dijkstra for non-negative; Bellman-Ford for negative)
  * Idempotency caching
  * Timeout handling
  * Structured logging
  * Retry logic with exponential backoff

All errors wrapped in RoutingResult; no exceptions raised to caller.
Every request traced with unique request_id for audit & debugging.
"""

import time
import heapq
import json
import hashlib
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Set, Any
from datetime import datetime
from enum import Enum
import threading


# ===========================
# Configuration & Policy
# ===========================

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class RetryPolicy:
    """Retry configuration with exponential backoff."""
    max_retries: int = 3
    initial_delay_ms: int = 100
    backoff_multiplier: float = 2.0
    max_delay_ms: int = 5000
    jitter_enabled: bool = True


@dataclass
class RoutingConfig:
    """Configuration for routing computation."""
    timeout_ms: int = 1000
    algorithm_hint: str = "auto"  # "dijkstra", "bellman_ford", or "auto"
    cache_enabled: bool = True
    cache_ttl_sec: int = 300
    retry_policy: Optional[RetryPolicy] = field(default_factory=RetryPolicy)
    
    def __post_init__(self):
        if self.retry_policy is None:
            self.retry_policy = RetryPolicy()


# ===========================
# Data Models
# ===========================

@dataclass
class Graph:
    """Directed weighted graph using adjacency dict."""
    edges: List[Dict[str, Any]] = field(default_factory=list)
    _adj: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Build adjacency dict from edges list."""
        for edge in self.edges:
            src = edge.get("source")
            dst = edge.get("target")
            weight = edge.get("weight", 0.0)
            if src and dst:
                if src not in self._adj:
                    self._adj[src] = {}
                self._adj[src][dst] = weight
                if dst not in self._adj:
                    self._adj[dst] = {}
    
    def neighbors(self, node: str) -> Dict[str, float]:
        """Return neighbors and edge weights."""
        return self._adj.get(node, {})
    
    def nodes(self) -> List[str]:
        """Return all nodes."""
        return list(self._adj.keys())
    
    def to_dict(self) -> dict:
        return {"edges": self.edges}


@dataclass
class GraphValidation:
    """Result of graph validation."""
    is_valid: bool
    node_count: int
    edge_count: int
    has_negative_weights: bool
    has_negative_cycle: bool
    is_weakly_connected: bool
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RoutingResult:
    """Result of routing computation."""
    path: Optional[List[str]]
    cost: Optional[float]
    algorithm: Optional[str]
    request_id: str
    duration_ms: float
    status: str  # "success" or "error"
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    cache_hit: bool = False
    graph_validation: Optional[dict] = None
    retry_count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_log_entry(self) -> str:
        """Format as structured JSON log."""
        log_dict = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": self.request_id,
            "event_type": f"routing_{self.status}",
            "level": "INFO" if self.status == "success" else "ERROR",
            "service": "logistics-routing-v2",
            "path": self.path,
            "cost": self.cost,
            "algorithm": self.algorithm,
            "duration_ms": round(self.duration_ms, 2),
            "error_code": self.error_code,
            "error_message": self.error_message,
            "cache_hit": self.cache_hit,
            "retry_count": self.retry_count,
            "graph_validation": self.graph_validation,
        }
        return json.dumps(log_dict)


# ===========================
# Shortest-Path Algorithms
# ===========================

def dijkstra_shortest_path(
    graph: Graph,
    start: str,
    goal: str,
    timeout_ms: int = 1000,
    request_id: str = None
) -> Tuple[List[str], float]:
    """
    Dijkstra's algorithm for non-negative-weight graphs.
    
    **Correctness fixes from v1:**
    1. Nodes marked visited ONLY when popped (finalized), not on discovery.
    2. Upstream validates no negative weights.
    
    Args:
        graph: Directed graph with non-negative weights only.
        start: Start node.
        goal: Goal node.
        timeout_ms: Max execution time.
        request_id: For logging.
    
    Returns:
        (path, cost) tuple.
    
    Raises:
        ValueError: If start/goal not in graph.
        TimeoutError: If computation exceeds timeout_ms.
    
    Time: O(|E| log|V|)
    Space: O(|V|)
    """
    nodes = graph.nodes()
    if start not in nodes:
        raise ValueError(f"Start node '{start}' not in graph")
    if goal not in nodes:
        raise ValueError(f"Goal node '{goal}' not in graph")
    
    start_time = time.time()
    
    # Distance and predecessor tracking
    dist: Dict[str, float] = {node: float("inf") for node in nodes}
    dist[start] = 0.0
    prev: Dict[str, Optional[str]] = {node: None for node in nodes}
    
    # Min-heap: (cost, node)
    heap: List[Tuple[float, str]] = [(0.0, start)]
    
    # Visited set: nodes finalized (popped from heap)
    visited: Set[str] = set()
    
    while heap:
        # Check timeout
        elapsed = (time.time() - start_time) * 1000
        if elapsed > timeout_ms:
            raise TimeoutError(
                f"Dijkstra computation exceeded {timeout_ms}ms (elapsed: {elapsed:.1f}ms)"
            )
        
        cost, node = heapq.heappop(heap)
        
        # Skip if already finalized (stale entry)
        if node in visited:
            continue
        
        visited.add(node)  # Mark finalized
        
        # Found goal
        if node == goal:
            path = _reconstruct_path(prev, goal)
            elapsed = (time.time() - start_time) * 1000
            _log_debug(
                f"Dijkstra: Found path {path} (cost={cost:.1f}, {elapsed:.1f}ms)",
                request_id=request_id
            )
            return path, cost
        
        # Relax outgoing edges
        for neighbor, weight in graph.neighbors(node).items():
            if neighbor in visited:
                continue  # Already finalized
            
            new_cost = cost + weight
            if new_cost < dist[neighbor]:
                dist[neighbor] = new_cost
                prev[neighbor] = node
                heapq.heappush(heap, (new_cost, neighbor))
    
    raise ValueError(f"No path found from {start} to {goal}")


def bellman_ford_shortest_path(
    graph: Graph,
    start: str,
    goal: str,
    timeout_ms: int = 1000,
    request_id: str = None
) -> Tuple[List[str], float]:
    """
    Bellman-Ford algorithm for graphs with negative edges (no negative cycles).
    
    Algorithm:
    1. Initialize dist[start] = 0, dist[others] = ∞.
    2. Relax all edges |V|-1 times.
    3. Check for negative cycles (attempt one more relaxation).
    4. Reconstruct path.
    
    Args:
        graph: Directed graph (may contain negative weights).
        start: Start node.
        goal: Goal node.
        timeout_ms: Max execution time.
        request_id: For logging.
    
    Returns:
        (path, cost) tuple.
    
    Raises:
        ValueError: If start/goal not in graph or negative cycle detected.
        TimeoutError: If computation exceeds timeout_ms.
    
    Time: O(|V| * |E|)
    Space: O(|V|)
    """
    nodes = graph.nodes()
    if start not in nodes:
        raise ValueError(f"Start node '{start}' not in graph")
    if goal not in nodes:
        raise ValueError(f"Goal node '{goal}' not in graph")
    
    start_time = time.time()
    
    dist: Dict[str, float] = {node: float("inf") for node in nodes}
    dist[start] = 0.0
    prev: Dict[str, Optional[str]] = {node: None for node in nodes}
    
    # Relax edges |V|-1 times
    for iteration in range(len(nodes) - 1):
        elapsed = (time.time() - start_time) * 1000
        if elapsed > timeout_ms:
            raise TimeoutError(
                f"Bellman-Ford computation exceeded {timeout_ms}ms "
                f"(iteration {iteration}/{len(nodes)-1}, elapsed: {elapsed:.1f}ms)"
            )
        
        updated = False
        for u in nodes:
            if dist[u] == float("inf"):
                continue
            for v, weight in graph.neighbors(u).items():
                if dist[u] + weight < dist[v]:
                    dist[v] = dist[u] + weight
                    prev[v] = u
                    updated = True
        
        if not updated:
            break  # Early exit: no more improvements
    
    # Check for negative cycles
    elapsed = (time.time() - start_time) * 1000
    if elapsed > timeout_ms:
        raise TimeoutError(f"Bellman-Ford negative-cycle check exceeded {timeout_ms}ms")
    
    for u in nodes:
        if dist[u] == float("inf"):
            continue
        for v, weight in graph.neighbors(u).items():
            if dist[u] + weight < dist[v]:
                raise ValueError(
                    f"Negative cycle detected in graph (cycle reachable from {start})"
                )
    
    if dist[goal] == float("inf"):
        raise ValueError(f"No path found from {start} to {goal}")
    
    path = _reconstruct_path(prev, goal)
    elapsed = (time.time() - start_time) * 1000
    _log_debug(
        f"Bellman-Ford: Found path {path} (cost={dist[goal]:.1f}, {elapsed:.1f}ms)",
        request_id=request_id
    )
    return path, dist[goal]


def _reconstruct_path(prev: Dict[str, Optional[str]], goal: str) -> List[str]:
    """Reconstruct path from predecessor map."""
    path: List[str] = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path))


# ===========================
# Validation & Analysis
# ===========================

def _validate_graph(graph: Graph, start: str, goal: str) -> Tuple[bool, List[str]]:
    """Validate graph preconditions. Returns (is_valid, error_codes)."""
    errors: List[str] = []
    nodes = graph.nodes()
    
    if not nodes:
        errors.append("EMPTY_GRAPH")
        return False, errors
    
    if start not in nodes:
        errors.append("NODE_NOT_FOUND")
    if goal not in nodes:
        errors.append("NODE_NOT_FOUND")
    
    if errors:
        return False, errors
    
    # Check for negative cycle if graph has negative edges
    if _has_negative_weights(graph):
        if _has_negative_cycle(graph):
            errors.append("NEG_CYCLE")
    
    # Check if goal reachable from start
    if not _is_reachable(graph, start, goal):
        errors.append("NO_PATH_FOUND")
    
    return len(errors) == 0, errors


def _has_negative_weights(graph: Graph) -> bool:
    """Check if any edge has negative weight."""
    for edge in graph.edges:
        if edge.get("weight", 0.0) < 0:
            return True
    return False


def _has_negative_cycle(graph: Graph) -> bool:
    """Detect negative cycle using Bellman-Ford principle."""
    nodes = graph.nodes()
    if not nodes:
        return False
    
    dist: Dict[str, float] = {n: float("inf") for n in nodes}
    dist[nodes[0]] = 0.0  # Start from arbitrary node
    
    # Relax |V|-1 times
    for _ in range(len(nodes) - 1):
        for u in nodes:
            if dist[u] == float("inf"):
                continue
            for v, weight in graph.neighbors(u).items():
                if dist[u] + weight < dist[v]:
                    dist[v] = dist[u] + weight
    
    # If any edge can still be relaxed, cycle exists
    for u in nodes:
        if dist[u] == float("inf"):
            continue
        for v, weight in graph.neighbors(u).items():
            if dist[u] + weight < dist[v]:
                return True
    
    return False


def _is_reachable(graph: Graph, start: str, goal: str) -> bool:
    """Check if goal is reachable from start using BFS."""
    if start == goal:
        return True
    
    visited: Set[str] = set()
    queue: List[str] = [start]
    
    while queue:
        node = queue.pop(0)
        if node == goal:
            return True
        if node in visited:
            continue
        visited.add(node)
        for neighbor in graph.neighbors(node):
            if neighbor not in visited:
                queue.append(neighbor)
    
    return False


def _get_graph_stats(graph: Graph) -> GraphValidation:
    """Compute graph statistics for validation metadata."""
    nodes = graph.nodes()
    edges = graph.edges
    has_neg = _has_negative_weights(graph)
    has_cycle = _has_negative_cycle(graph) if has_neg else False
    
    return GraphValidation(
        is_valid=True,
        node_count=len(nodes),
        edge_count=len(edges),
        has_negative_weights=has_neg,
        has_negative_cycle=has_cycle,
        is_weakly_connected=len(nodes) > 0,  # Simplified
        validation_errors=[]
    )


# ===========================
# Main Routing Service
# ===========================

class RoutingService:
    """Main service: graph validation, algorithm selection, caching, logging."""
    
    def __init__(self, config: Optional[RoutingConfig] = None):
        self.config = config or RoutingConfig()
        self.cache: Dict[str, RoutingResult] = {}
        self.cache_access_times: Dict[str, float] = {}
        self.cache_lock = threading.Lock()
        self.logger = _get_logger()
    
    def compute_shortest_path(
        self,
        graph: Graph,
        start: str,
        goal: str,
        request_id: str = None,
        config: Optional[RoutingConfig] = None
    ) -> RoutingResult:
        """
        Compute shortest path with full validation, caching, and logging.
        
        Returns RoutingResult with status="success" or "error".
        No exceptions raised to caller.
        
        Args:
            graph: Directed weighted graph.
            start: Start node.
            goal: Goal node.
            request_id: Unique request ID (auto-generated if not provided).
            config: Routing config (uses self.config if not provided).
        
        Returns:
            RoutingResult with complete metadata.
        """
        start_time = time.time()
        request_id = request_id or str(uuid.uuid4())
        config = config or self.config
        
        try:
            # Step 1: Check idempotency cache
            if config.cache_enabled:
                cached = self._get_cached_result(graph, start, goal)
                if cached:
                    elapsed = (time.time() - start_time) * 1000
                    cached.cache_hit = True
                    cached.duration_ms = elapsed
                    self._log_result(cached)
                    return cached
            
            # Step 2: Validate graph
            is_valid, errors = _validate_graph(graph, start, goal)
            if not is_valid:
                result = RoutingResult(
                    path=None,
                    cost=None,
                    algorithm=None,
                    request_id=request_id,
                    duration_ms=(time.time() - start_time) * 1000,
                    status="error",
                    error_code=errors[0],  # First error code
                    error_message="; ".join(errors),
                    graph_validation=_get_graph_stats(graph).to_dict()
                )
                self._cache_result(graph, start, goal, result)
                self._log_result(result)
                return result
            
            # Step 3: Get graph stats
            graph_stats = _get_graph_stats(graph)
            
            # Step 4: Select algorithm
            has_neg_weights = graph_stats.has_negative_weights
            algorithm = self._select_algorithm(has_neg_weights, config)
            
            # Step 5: Compute path with retry logic
            path, cost, algo_used = self._compute_with_retry(
                graph, start, goal, algorithm, config, request_id
            )
            
            result = RoutingResult(
                path=path,
                cost=cost,
                algorithm=algo_used,
                request_id=request_id,
                duration_ms=(time.time() - start_time) * 1000,
                status="success",
                error_code=None,
                error_message=None,
                graph_validation=graph_stats.to_dict()
            )
            
            self._cache_result(graph, start, goal, result)
            self._log_result(result)
            return result
        
        except Exception as e:
            # Catch-all for unexpected errors
            _log_error(f"Unexpected error in compute_shortest_path: {str(e)}", request_id)
            result = RoutingResult(
                path=None,
                cost=None,
                algorithm=None,
                request_id=request_id,
                duration_ms=(time.time() - start_time) * 1000,
                status="error",
                error_code="INTERNAL_ERROR",
                error_message=str(e)
            )
            self._log_result(result)
            return result
    
    def _compute_with_retry(
        self,
        graph: Graph,
        start: str,
        goal: str,
        algorithm: str,
        config: RoutingConfig,
        request_id: str
    ) -> Tuple[List[str], float, str]:
        """Compute path with retry logic."""
        policy = config.retry_policy
        last_error = None
        
        for attempt in range(policy.max_retries):
            try:
                if algorithm == "dijkstra":
                    path, cost = dijkstra_shortest_path(
                        graph, start, goal, config.timeout_ms, request_id
                    )
                else:
                    path, cost = bellman_ford_shortest_path(
                        graph, start, goal, config.timeout_ms, request_id
                    )
                
                if attempt > 0:
                    _log_info(f"Retry succeeded on attempt {attempt+1}", request_id)
                
                return path, cost, algorithm
            
            except (TimeoutError, ValueError) as e:
                last_error = e
                if attempt < policy.max_retries - 1:
                    delay = policy.initial_delay_ms * (policy.backoff_multiplier ** attempt)
                    if policy.jitter_enabled:
                        import random
                        delay = delay * (0.5 + random.random())
                    delay = min(delay, policy.max_delay_ms) / 1000.0
                    _log_info(
                        f"Retry attempt {attempt+1}: {str(e)}; backoff {delay*1000:.0f}ms",
                        request_id
                    )
                    time.sleep(delay)
        
        # Exhausted retries
        raise last_error if last_error else ValueError("Computation failed")
    
    def _select_algorithm(self, has_neg_weights: bool, config: RoutingConfig) -> str:
        """Select algorithm based on graph characteristics."""
        if config.algorithm_hint in ["dijkstra", "bellman_ford"]:
            return config.algorithm_hint
        # "auto"
        return "bellman_ford" if has_neg_weights else "dijkstra"
    
    def _get_cached_result(self, graph: Graph, start: str, goal: str) -> Optional[RoutingResult]:
        """Look up result in idempotency cache."""
        key = self._get_cache_key(graph, start, goal)
        with self.cache_lock:
            if key in self.cache:
                access_time = self.cache_access_times.get(key, 0)
                if time.time() - access_time < self.config.cache_ttl_sec:
                    self.cache_access_times[key] = time.time()
                    return self.cache[key]
                else:
                    del self.cache[key]
        return None
    
    def _cache_result(
        self,
        graph: Graph,
        start: str,
        goal: str,
        result: RoutingResult
    ) -> None:
        """Store result in idempotency cache."""
        key = self._get_cache_key(graph, start, goal)
        with self.cache_lock:
            self.cache[key] = result
            self.cache_access_times[key] = time.time()
    
    def _get_cache_key(self, graph: Graph, start: str, goal: str) -> str:
        """Generate deterministic cache key."""
        graph_hash = hashlib.sha256(
            json.dumps(graph.to_dict(), sort_keys=True).encode()
        ).hexdigest()
        return hashlib.sha256(
            f"{graph_hash}|{start}|{goal}".encode()
        ).hexdigest()
    
    def _log_result(self, result: RoutingResult) -> None:
        """Log result as structured JSON."""
        log_entry = result.to_log_entry()
        self.logger.info(log_entry)
    
    def cleanup_expired_cache(self) -> int:
        """Evict expired cache entries; return count removed."""
        now = time.time()
        ttl_sec = self.config.cache_ttl_sec
        with self.cache_lock:
            expired_keys = [
                k for k, t in self.cache_access_times.items()
                if now - t > ttl_sec
            ]
            for k in expired_keys:
                del self.cache[k]
                del self.cache_access_times[k]
        return len(expired_keys)


# ===========================
# Logging Utilities
# ===========================

def _get_logger():
    """Get or create logger."""
    logger = logging.getLogger("logistics.routing")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _log_info(message: str, request_id: str = None) -> None:
    """Log info message."""
    logger = _get_logger()
    prefix = f"[{request_id}] " if request_id else ""
    logger.info(prefix + message)


def _log_debug(message: str, request_id: str = None) -> None:
    """Log debug message."""
    logger = _get_logger()
    prefix = f"[{request_id}] " if request_id else ""
    logger.debug(prefix + message)


def _log_error(message: str, request_id: str = None) -> None:
    """Log error message."""
    logger = _get_logger()
    prefix = f"[{request_id}] " if request_id else ""
    logger.error(prefix + message)


# ===========================
# Module-Level Service Instance
# ===========================

_default_service: Optional[RoutingService] = None


def get_service(config: Optional[RoutingConfig] = None) -> RoutingService:
    """Get or create default routing service."""
    global _default_service
    if _default_service is None:
        _default_service = RoutingService(config)
    return _default_service


# ===========================
# Public API
# ===========================

def compute_shortest_path(
    graph: Graph,
    start: str,
    goal: str,
    request_id: str = None,
    config: Optional[RoutingConfig] = None
) -> RoutingResult:
    """
    Public API: compute shortest path.
    
    Args:
        graph: Directed weighted graph.
        start: Start node.
        goal: Goal node.
        request_id: Unique request ID (auto-generated if not provided).
        config: Routing configuration.
    
    Returns:
        RoutingResult (never raises exceptions).
    """
    service = get_service(config)
    return service.compute_shortest_path(graph, start, goal, request_id, config)


if __name__ == "__main__":
    # Example usage
    graph = Graph(edges=[
        {"source": "A", "target": "B", "weight": 5},
        {"source": "A", "target": "C", "weight": 2},
        {"source": "C", "target": "D", "weight": 1},
        {"source": "D", "target": "F", "weight": -3},
        {"source": "F", "target": "B", "weight": 1},
    ])
    
    result = compute_shortest_path(graph, "A", "B", request_id="example_001")
    print(f"Path: {result.path}")
    print(f"Cost: {result.cost}")
    print(f"Algorithm: {result.algorithm}")
    print(f"Status: {result.status}")
    print(f"Duration: {result.duration_ms:.2f}ms")
