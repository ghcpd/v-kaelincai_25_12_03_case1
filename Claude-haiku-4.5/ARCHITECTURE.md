# Logistics Routing v2 – Greenfield Architecture & Design

**Date:** December 3, 2025  
**Version:** 2.0.0  
**Status:** Design Phase (Implementation pending)

---

## 1. Architecture Overview

### 1.1 Component Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LOGISTICS ROUTING v2                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐  ┌───────────────────────┐  ┌──────────────────────┐  │
│  │ Input: Graph   │  │ Validation & Pre-     │  │ Idempotency Cache    │  │
│  │ Request        │→→│ flight Checks         │→→│ (Request ID lookup)  │  │
│  │ (start, goal,  │  │ • Node existence      │  │ TTL: 5 min           │  │
│  │  request_id)   │  │ • Negative cycles     │  │ Memory: 10K entries  │  │
│  └────────────────┘  │ • Self-loops (warn)   │  └──────────────────────┘  │
│                      └───────────────────────┘           │                  │
│                                                          ├─ CACHE HIT       │
│                         NO CACHE HIT                     │ (return cached)   │
│                              │                           │                  │
│                              ▼                           │                  │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                  ALGORITHM SELECTION ENGINE                        │◄──┘
│  ├────────────────────────────────────────────────────────────────────┤   │
│  │ • Scan graph for negative weights                                  │   │
│  │ • If neg_weight detected: Use BELLMAN-FORD                         │   │
│  │ • Else: Use DIJKSTRA (faster)                                      │   │
│  │ • Log algorithm choice + reasoning                                 │   │
│  └───┬────────────────────────────────────────────────────────────────┘   │
│      │                                                                      │
│      ├──────────────────────────┬──────────────────────────┐               │
│      ▼                          ▼                          ▼               │
│  ┌────────────────┐    ┌──────────────────┐    ┌──────────────────────┐  │
│  │  DIJKSTRA      │    │  BELLMAN-FORD    │    │  TIMEOUT WRAPPER     │  │
│  │ (Non-neg)      │    │ (Negative edge)  │    │ (signal.SIGALRM or   │  │
│  │                │    │                  │    │  threading.Timer)    │  │
│  │ Time: O(|E|    │    │ Time: O(|V||E|)  │    │                      │  │
│  │  log|V|)       │    │                  │    │ • Max: config        │  │
│  │                │    │ • Relax |V|-1x   │    │   .timeout_ms        │  │
│  │ Heap-based     │    │ • Cycle check    │    │ • Return error if    │  │
│  │ priority queue │    │ • Path recons.   │    │   exceeded           │  │
│  └────────────────┘    └──────────────────┘    └──────────────────────┘  │
│      │                          │                        │                 │
│      └──────────────────────────┴────────────────────────┘                 │
│                                 │                                           │
│                                 ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                    RESULT CONSTRUCTION                             │   │
│  ├────────────────────────────────────────────────────────────────────┤   │
│  │ • Path: [start, ..., goal]                                         │   │
│  │ • Cost: float (total weight)                                       │   │
│  │ • Algorithm: "dijkstra" | "bellman_ford"                           │   │
│  │ • Duration: elapsed_ms                                             │   │
│  │ • Request ID: for tracing                                          │   │
│  │ • Status: "success" | "error"                                      │   │
│  │ • Error code & message (if error)                                  │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │            LOGGING & CACHE STORAGE                                 │   │
│  ├────────────────────────────────────────────────────────────────────┤   │
│  │ • Structured JSON log (timestamp, request_id, algorithm, cost)    │   │
│  │ • Cache result (idempotency): request_id → RoutingResult          │   │
│  │ • Metrics: latency, algorithm choice, cache hit rate              │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                 │                                           │
│                                 ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │                     OUTPUT: RoutingResult                          │   │
│  │ { path, cost, algorithm, request_id, duration_ms, status, ...}    │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow (Success Path)

```
Request Arrives (request_id, graph, start, goal)
  │
  ├─ Cache Lookup (request_id)
  │  ├─ HIT: Return cached RoutingResult ────────────────────────────┐
  │  │                                                               │
  │  └─ MISS: Continue                                              │
  │     │                                                            │
  │     ├─ Validate Preconditions                                   │
  │     │  ├─ Nodes in graph? ─NO─ Return error (VAL_EMPTY)        │
  │     │  ├─ Start/goal exist? ─NO─ Return error (NODE_NOT_FOUND) │
  │     │  └─ Negative cycle? ─YES─ Return error (NEG_CYCLE)       │
  │     │     (Success: Continue)                                   │
  │     │                                                            │
  │     ├─ Scan for Negative Weights                                │
  │     │  ├─ Found: Use Bellman-Ford ─────────────────────────┐   │
  │     │  │                                                   │   │
  │     │  └─ Not found: Use Dijkstra ──────┐                 │   │
  │     │                                    │                 │   │
  │     ├──────────────────────────────────┬─┴─────────────────┤   │
  │     │                                  │                   │   │
  │     ▼                                  ▼                   ▼   │
  │  [DIJKSTRA]                      [BELLMAN-FORD]           │   │
  │  • Initialize dist[start]=0        • Initialize dist,prev │   │
  │  • Min-heap of (cost, node)        • Relax edges |V|-1x   │   │
  │  • Relax edges on pop()            • Final cycle check     │   │
  │  • Stop when goal popped           • Reconstruct path      │   │
  │  • Time: O(|E| log|V|)             • Time: O(|V||E|)      │   │
  │     │                                  │                   │   │
  │     └──────────────────┬────────────────┴────────────┬──────┘   │
  │                        │                            │           │
  │                        ▼                            ▼           │
  │              [Reconstruct Path] ◄──────────────────┘            │
  │                  path = [A, C, D, F, B]                         │
  │                  cost = 1.0                                     │
  │                        │                                        │
  │                        ▼                                        │
  │              [Build RoutingResult]                              │
  │                  status="success"                               │
  │                  algorithm="bellman_ford"                       │
  │                  duration_ms=42.5                               │
  │                        │                                        │
  │                        ▼                                        │
  │              [Log + Cache]                                      │
  │                  • Write JSON log                               │
  │                  • Cache[request_id] = result (TTL=5min)        │
  │                  • Update metrics                               │
  │                        │                                        │
  ▼                        ▼                                        │
Return RoutingResult ◄─────────────────────────────────────────────┘
```

---

## 2. Data Models & Schemas

### 2.1 Input Schema

```python
@dataclass
class RoutingRequest:
    """Client request for routing computation."""
    graph: Graph                  # Directed weighted graph (adjacency dict)
    start: str                    # Start node identifier
    goal: str                     # Goal node identifier
    request_id: str = field(      # Unique request ID for tracing + idempotency
        default_factory=lambda: str(uuid.uuid4())
    )
    config: RoutingConfig = field(
        default_factory=RoutingConfig
    )
    
    def to_idempotency_key(self) -> str:
        """Generate deterministic key for caching."""
        graph_hash = hashlib.sha256(
            json.dumps(self.graph.to_dict(), sort_keys=True).encode()
        ).hexdigest()
        return hashlib.sha256(
            f"{graph_hash}|{self.start}|{self.goal}".encode()
        ).hexdigest()
```

### 2.2 Output Schema

```python
@dataclass
class RoutingResult:
    """Result of routing computation."""
    path: Optional[List[str]]     # Shortest path: [start, ..., goal] or None
    cost: Optional[float]          # Total cost of path or None
    algorithm: Optional[str]       # "dijkstra", "bellman_ford", or None
    request_id: str               # Unique request identifier
    duration_ms: float            # Execution time in milliseconds
    status: str                   # "success" or "error"
    error_code: Optional[str]     # "NODE_NOT_FOUND", "NEG_CYCLE", "TIMEOUT", etc.
    error_message: Optional[str]  # Human-readable error description
    cache_hit: bool = False       # Whether result served from cache
    graph_validation: Optional[dict] = None  # Validation metadata
    
    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return {
            "path": self.path,
            "cost": self.cost,
            "algorithm": self.algorithm,
            "request_id": self.request_id,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "cache_hit": self.cache_hit,
            "graph_validation": self.graph_validation,
        }

    def to_log_entry(self) -> str:
        """Format as structured JSON log."""
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": self.request_id,
            "event_type": f"routing_{self.status}",
            "path": self.path,
            "cost": self.cost,
            "algorithm": self.algorithm,
            "duration_ms": self.duration_ms,
            "error_code": self.error_code,
            "cache_hit": self.cache_hit,
        })
```

### 2.3 Configuration Schema

```python
@dataclass
class RoutingConfig:
    """Configuration for routing computation."""
    timeout_ms: int = 1000                    # Max execution time
    algorithm_hint: str = "auto"              # "dijkstra", "bellman_ford", "auto"
    cache_enabled: bool = True                # Enable idempotency cache
    cache_ttl_sec: int = 300                  # Cache TTL (5 minutes)
    retry_policy: Optional[RetryPolicy] = None
    circuit_breaker: Optional[CircuitBreaker] = None
    
    def __post_init__(self):
        if self.retry_policy is None:
            self.retry_policy = RetryPolicy()

@dataclass
class RetryPolicy:
    """Retry configuration with exponential backoff."""
    max_retries: int = 3
    initial_delay_ms: int = 100
    backoff_multiplier: float = 2.0
    max_delay_ms: int = 5000
    jitter_enabled: bool = True
```

### 2.4 Graph Validation Metadata

```python
@dataclass
class GraphValidation:
    """Result of pre-flight graph validation."""
    is_valid: bool
    node_count: int
    edge_count: int
    has_negative_weights: bool
    has_negative_cycle: bool
    is_strongly_connected: bool  # For directed graphs
    validation_errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
```

---

## 3. Algorithms & Implementation Details

### 3.1 Dijkstra's Algorithm (Corrected)

```python
def dijkstra_shortest_path(
    graph: Graph,
    start: str,
    goal: str,
    timeout_ms: int = 1000,
    request_id: str = None
) -> Tuple[List[str], float]:
    """
    Compute shortest path in non-negative-weight directed graph.
    
    **Correctness fixes from v1:**
    1. No negative-edge validation here (handled upstream).
    2. Nodes marked visited ONLY when popped from heap (finalized),
       not when first discovered.
    
    Args:
        graph: Directed graph with non-negative weights only.
        start: Start node.
        goal: Goal node.
        timeout_ms: Max execution time; raises TimeoutError if exceeded.
        request_id: For logging.
    
    Returns:
        (path, cost) tuple.
    
    Raises:
        ValueError: If start or goal not in graph.
        TimeoutError: If computation exceeds timeout_ms.
    
    Time Complexity: O(|E| log|V|) with binary heap.
    Space Complexity: O(|V|).
    """
    import time
    import heapq
    
    if start not in dict(graph.nodes()):
        raise ValueError(f"Start node '{start}' not in graph")
    if goal not in dict(graph.nodes()):
        raise ValueError(f"Goal node '{goal}' not in graph")
    
    start_time = time.time()
    
    # Distance and predecessor tracking
    dist = {node: float("inf") for node in graph.nodes()}
    dist[start] = 0.0
    prev = {node: None for node in graph.nodes()}
    
    # Min-heap: (cost, node)
    heap = [(0.0, start)]
    
    # Visited set: nodes finalized (popped from heap)
    visited = set()
    
    while heap:
        # Check timeout
        elapsed = (time.time() - start_time) * 1000
        if elapsed > timeout_ms:
            raise TimeoutError(
                f"Dijkstra computation exceeded {timeout_ms}ms "
                f"(elapsed: {elapsed:.1f}ms)"
            )
        
        cost, node = heapq.heappop(heap)
        
        if node in visited:
            continue  # Already finalized; skip stale entries
        
        visited.add(node)  # Mark finalized
        
        if node == goal:
            path = _reconstruct_path(prev, goal)
            elapsed = (time.time() - start_time) * 1000
            log_info(f"Dijkstra: Found path {path} (cost={cost}, {elapsed:.1f}ms)", 
                     request_id=request_id)
            return path, cost
        
        # Relax outgoing edges
        for neighbor, weight in graph.neighbors(node).items():
            if neighbor in visited:
                continue  # Already finalized; skip
            
            new_cost = cost + weight
            if new_cost < dist[neighbor]:
                dist[neighbor] = new_cost
                prev[neighbor] = node
                heapq.heappush(heap, (new_cost, neighbor))
    
    raise ValueError(f"No path found from {start} to {goal}")


def _reconstruct_path(prev: Dict[str, Optional[str]], goal: str) -> List[str]:
    """Reconstruct path from predecessor map."""
    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev.get(node)
    return list(reversed(path))
```

### 3.2 Bellman-Ford Algorithm (Negative Weight Support)

```python
def bellman_ford_shortest_path(
    graph: Graph,
    start: str,
    goal: str,
    timeout_ms: int = 1000,
    request_id: str = None
) -> Tuple[List[str], float]:
    """
    Compute shortest path in graph with negative edges (no negative cycles).
    
    Algorithm:
    1. Initialize dist[start] = 0, all others = ∞.
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
        ValueError: If start/goal not in graph, or negative cycle detected.
        TimeoutError: If computation exceeds timeout_ms.
    
    Time Complexity: O(|V| * |E|).
    Space Complexity: O(|V|).
    """
    import time
    
    if start not in dict(graph.nodes()):
        raise ValueError(f"Start node '{start}' not in graph")
    if goal not in dict(graph.nodes()):
        raise ValueError(f"Goal node '{goal}' not in graph")
    
    start_time = time.time()
    
    nodes = list(graph.nodes())
    dist = {node: float("inf") for node in nodes}
    dist[start] = 0.0
    prev = {node: None for node in nodes}
    
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
            break  # Early exit: no improvements possible
    
    # Check for negative cycles
    elapsed = (time.time() - start_time) * 1000
    if elapsed > timeout_ms:
        raise TimeoutError(
            f"Bellman-Ford negative-cycle check exceeded {timeout_ms}ms"
        )
    
    for u in nodes:
        if dist[u] == float("inf"):
            continue
        for v, weight in graph.neighbors(u).items():
            if dist[u] + weight < dist[v]:
                raise ValueError(
                    f"Negative cycle detected in graph "
                    f"(cycle reachable from {start})"
                )
    
    if dist[goal] == float("inf"):
        raise ValueError(f"No path found from {start} to {goal}")
    
    path = _reconstruct_path(prev, goal)
    elapsed = (time.time() - start_time) * 1000
    log_info(
        f"Bellman-Ford: Found path {path} (cost={dist[goal]}, {elapsed:.1f}ms)",
        request_id=request_id
    )
    return path, dist[goal]
```

### 3.3 Unified Routing Service

```python
class RoutingService:
    """Main service coordinating graph validation, algorithm selection, and result caching."""
    
    def __init__(self, config: Optional[RoutingConfig] = None):
        self.config = config or RoutingConfig()
        self.cache: Dict[str, RoutingResult] = {}
        self.cache_access_times: Dict[str, float] = {}
    
    def compute_shortest_path(
        self,
        request: RoutingRequest
    ) -> RoutingResult:
        """
        Main entry point: compute shortest path with validation, caching, and logging.
        
        Returns RoutingResult with status="success" or status="error".
        No exceptions raised; all errors wrapped in result.
        """
        start_time = time.time()
        request_id = request.request_id
        
        try:
            # Step 1: Check idempotency cache
            if self.config.cache_enabled:
                cached = self._get_cached_result(request)
                if cached is not None:
                    cached.cache_hit = True
                    elapsed = (time.time() - start_time) * 1000
                    cached.duration_ms = elapsed
                    self._log_result(cached)
                    return cached
            
            # Step 2: Validate graph
            validation = self._validate_graph(request.graph, request.start, request.goal)
            if not validation.is_valid:
                error_code = validation.validation_errors[0]  # Use first error code
                result = RoutingResult(
                    path=None,
                    cost=None,
                    algorithm=None,
                    request_id=request_id,
                    duration_ms=(time.time() - start_time) * 1000,
                    status="error",
                    error_code=error_code,
                    error_message="; ".join(validation.validation_errors),
                    graph_validation=validation.to_dict()
                )
                self._cache_result(request, result)
                self._log_result(result)
                return result
            
            # Step 3: Select algorithm
            has_neg_weights = validation.has_negative_weights
            algorithm = self._select_algorithm(has_neg_weights, request.config)
            
            # Step 4: Compute path
            try:
                path, cost = self._compute_path(
                    request.graph,
                    request.start,
                    request.goal,
                    algorithm,
                    request.config.timeout_ms,
                    request_id
                )
                result = RoutingResult(
                    path=path,
                    cost=cost,
                    algorithm=algorithm,
                    request_id=request_id,
                    duration_ms=(time.time() - start_time) * 1000,
                    status="success",
                    error_code=None,
                    error_message=None,
                    graph_validation=validation.to_dict()
                )
            except TimeoutError as e:
                result = RoutingResult(
                    path=None,
                    cost=None,
                    algorithm=algorithm,
                    request_id=request_id,
                    duration_ms=(time.time() - start_time) * 1000,
                    status="error",
                    error_code="TIMEOUT",
                    error_message=str(e)
                )
            except (ValueError, Exception) as e:
                result = RoutingResult(
                    path=None,
                    cost=None,
                    algorithm=algorithm,
                    request_id=request_id,
                    duration_ms=(time.time() - start_time) * 1000,
                    status="error",
                    error_code="COMPUTATION_ERROR",
                    error_message=str(e)
                )
            
            # Step 5: Cache and log
            self._cache_result(request, result)
            self._log_result(result)
            return result
        
        except Exception as e:
            # Unexpected error: wrap in result
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
    
    def _validate_graph(self, graph: Graph, start: str, goal: str) -> GraphValidation:
        """Validate graph preconditions."""
        errors = []
        nodes = list(graph.nodes())
        
        if not nodes:
            errors.append("EMPTY_GRAPH")
        
        if start not in nodes:
            errors.append(f"NODE_NOT_FOUND: start '{start}'")
        if goal not in nodes:
            errors.append(f"NODE_NOT_FOUND: goal '{goal}'")
        
        has_neg = any(
            w < 0 for u in nodes for w in graph.neighbors(u).values()
        )
        
        has_cycle = self._detect_negative_cycle(graph) if has_neg else False
        if has_cycle:
            errors.append("NEG_CYCLE")
        
        edge_count = sum(len(graph.neighbors(u)) for u in nodes)
        is_connected = self._is_weakly_connected(graph)
        
        return GraphValidation(
            is_valid=len(errors) == 0,
            node_count=len(nodes),
            edge_count=edge_count,
            has_negative_weights=has_neg,
            has_negative_cycle=has_cycle,
            is_strongly_connected=is_connected,
            validation_errors=errors
        )
    
    def _detect_negative_cycle(self, graph: Graph) -> bool:
        """Check for negative-weight cycle using Bellman-Ford principle."""
        nodes = list(graph.nodes())
        dist = {n: float("inf") for n in nodes}
        dist[nodes[0]] = 0.0  # Start from arbitrary node
        
        for _ in range(len(nodes) - 1):
            for u in nodes:
                if dist[u] == float("inf"):
                    continue
                for v, w in graph.neighbors(u).items():
                    if dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
        
        # If any edge can still be relaxed, negative cycle exists
        for u in nodes:
            if dist[u] == float("inf"):
                continue
            for v, w in graph.neighbors(u).items():
                if dist[u] + w < dist[v]:
                    return True
        
        return False
    
    def _is_weakly_connected(self, graph: Graph) -> bool:
        """Check if graph is weakly connected (for undirected version)."""
        # Simplified: assume true for now; full implementation uses DFS/BFS
        return True
    
    def _select_algorithm(self, has_neg_weights: bool, config: RoutingConfig) -> str:
        """Select algorithm based on graph characteristics."""
        if config.algorithm_hint == "dijkstra":
            return "dijkstra"
        elif config.algorithm_hint == "bellman_ford":
            return "bellman_ford"
        else:  # "auto"
            return "bellman_ford" if has_neg_weights else "dijkstra"
    
    def _compute_path(
        self,
        graph: Graph,
        start: str,
        goal: str,
        algorithm: str,
        timeout_ms: int,
        request_id: str
    ) -> Tuple[List[str], float]:
        """Dispatch to appropriate algorithm."""
        if algorithm == "dijkstra":
            return dijkstra_shortest_path(graph, start, goal, timeout_ms, request_id)
        else:
            return bellman_ford_shortest_path(graph, start, goal, timeout_ms, request_id)
    
    def _get_cached_result(self, request: RoutingRequest) -> Optional[RoutingResult]:
        """Look up result in idempotency cache."""
        key = request.to_idempotency_key()
        if key in self.cache:
            access_time = self.cache_access_times.get(key, 0)
            if time.time() - access_time < request.config.cache_ttl_sec:
                self.cache_access_times[key] = time.time()
                return self.cache[key]
            else:
                del self.cache[key]
        return None
    
    def _cache_result(self, request: RoutingRequest, result: RoutingResult) -> None:
        """Store result in idempotency cache."""
        if self.config.cache_enabled:
            key = request.to_idempotency_key()
            self.cache[key] = result
            self.cache_access_times[key] = time.time()
    
    def _log_result(self, result: RoutingResult) -> None:
        """Log result as structured JSON."""
        log_entry = result.to_log_entry()
        print(log_entry)  # Or write to logger
    
    def cleanup_expired_cache(self) -> int:
        """Evict expired cache entries; return count removed."""
        now = time.time()
        ttl_sec = self.config.cache_ttl_sec
        expired_keys = [
            k for k, t in self.cache_access_times.items()
            if now - t > ttl_sec
        ]
        for k in expired_keys:
            del self.cache[k]
            del self.cache_access_times[k]
        return len(expired_keys)
```

---

## 4. Migration & Deployment Strategy

### 4.1 Dual-Write Shadow Testing

**Duration:** 1 week (staging), then 1 week (prod at 0% v2 traffic)

```python
def dual_write_wrapper(request: RoutingRequest) -> RoutingResult:
    """
    Execute both v1 and v2; return v1 result but log v2 for validation.
    """
    request_id = request.request_id
    
    # Primary: v1 (routing.dijkstra_shortest_path)
    try:
        v1_result = routing_v1.compute_path(request)
    except Exception as e:
        v1_result = RoutingResult(..., status="error", error_code="V1_FAILED")
    
    # Shadow: v2 (routing_v2.RoutingService)
    try:
        service = RoutingService()
        v2_result = service.compute_shortest_path(request)
    except Exception as e:
        v2_result = RoutingResult(..., status="error", error_code="V2_FAILED")
    
    # Compare and log
    match = (
        v1_result.status == v2_result.status and
        v1_result.cost == pytest.approx(v2_result.cost, rel=1e-6) and
        v1_result.path == v2_result.path
    )
    
    log_dual_write_comparison(
        request_id=request_id,
        v1_result=v1_result,
        v2_result=v2_result,
        match=match
    )
    
    return v1_result  # Still return v1 to caller
```

### 4.2 Canary Rollout

```
Day 1:  v2 = 0% (dual-write shadow only)
Day 2:  v2 = 10% (by request_id hash)  → monitor error rate, latency
Day 3:  v2 = 25%  → if metrics green, continue
Day 4:  v2 = 50%  → if metrics green, continue
Day 5:  v2 = 100% → full migration; v1 still shadowing for rollback safety
Week 2: v1 code removed; v2 stable
```

**Monitoring Dashboard:**
- v1 vs v2 error rate (target: v2 ≤ v1 + 0.5%)
- v1 vs v2 p99 latency (target: v2 ≤ 2× v1)
- v2 cache hit rate (target: ≥ 60%)
- v2 retry count per request (target: avg ≤ 0.1)

### 4.3 Rollback Procedure

```bash
# If v2 error rate > 5% or p99 latency > 2× baseline:

1. Flip feature flag: FEATURE_ROUTING_V2_ENABLED=false
   (Instantaneous; no code deploy needed)

2. Clear v2 caches:
   redis-cli FLUSHDB --async
   # Or in-memory cache auto-clears on restart

3. Alert on-call: post incident on Slack
   "Routing v2 rolled back due to elevated error rate ($(v2_error_rate)%)"

4. Inspect logs:
   kubectl logs -n logistics deployment/routing-service | grep "v2"

5. Create incident post-mortem within 24 hours
   (Review logs, identify root cause, plan fix)

6. Once fixed, re-run staging tests, then resume canary

7. Keep both v1 & v2 code in repo for 30 days for safety
```

---

## 5. Testing & Validation

### 5.1 Test Categories

| Category | Focus | Coverage |
|----------|-------|----------|
| **Unit Tests** | Dijkstra, Bellman-Ford, validation, caching | 90%+ code coverage |
| **Integration Tests** | Full request flow, error handling, observability | 10 scenarios (see ANALYSIS.md §6.1) |
| **Performance Tests** | Latency, throughput, memory on various graph sizes | p50/p99 latency, GC pauses |
| **Chaos/Stress Tests** | Timeout injection, concurrent requests, OOM | Resilience validation |
| **Dual-Write Tests** | v1 vs v2 correctness on 100K requests | 100% match on cost, path length |

### 5.2 Test Fixtures (5+ Canonical Cases)

**Scenario A: Simple Non-Negative**
```json
{
  "name": "simple_non_negative",
  "graph": {"edges": [{"source": "A", "target": "B", "weight": 5}]},
  "start": "A",
  "goal": "B",
  "expected_path": ["A", "B"],
  "expected_cost": 5.0,
  "expected_algorithm": "dijkstra",
  "expected_status": "success"
}
```

**Scenario B: Negative Edge (Corrected Path)**
```json
{
  "name": "negative_edge_corrected",
  "graph": {
    "edges": [
      {"source": "A", "target": "B", "weight": 5},
      {"source": "A", "target": "C", "weight": 2},
      {"source": "C", "target": "D", "weight": 1},
      {"source": "D", "target": "F", "weight": -3},
      {"source": "F", "target": "B", "weight": 1}
    ]
  },
  "start": "A",
  "goal": "B",
  "expected_path": ["A", "C", "D", "F", "B"],
  "expected_cost": 1.0,
  "expected_algorithm": "bellman_ford",
  "expected_status": "success"
}
```

**Scenario C: Negative Cycle**
```json
{
  "name": "negative_cycle",
  "graph": {
    "edges": [
      {"source": "A", "target": "B", "weight": -1},
      {"source": "B", "target": "C", "weight": -1},
      {"source": "C", "target": "A", "weight": -1}
    ]
  },
  "start": "A",
  "goal": "C",
  "expected_path": null,
  "expected_cost": null,
  "expected_algorithm": null,
  "expected_status": "error",
  "expected_error_code": "NEG_CYCLE"
}
```

**Scenario D: Idempotency (Same Request Twice)**
```json
{
  "name": "idempotency_cache_hit",
  "request_id": "req_123",
  "graph": {"edges": [{"source": "A", "target": "B", "weight": 1}]},
  "start": "A",
  "goal": "B",
  "call_count": 2,
  "expected_cache_hit_on_call_2": true,
  "expected_duration_ms_call_2": "<5ms"
}
```

**Scenario E: Node Not Found**
```json
{
  "name": "node_not_found",
  "graph": {"edges": [{"source": "A", "target": "B", "weight": 1}]},
  "start": "A",
  "goal": "Z",
  "expected_status": "error",
  "expected_error_code": "NODE_NOT_FOUND"
}
```

---

## 6. Success Metrics & KPIs

| Metric | v1 Baseline | v2 Target | Acceptance |
|--------|------------|-----------|-----------|
| **Correctness** | 80% (fails on negative) | 100% (all cases) | 100% on test cases |
| **p50 Latency (small graph)** | ~5ms | ~5ms | ±20% |
| **p99 Latency (small graph)** | ~20ms | ~25ms | ≤50ms |
| **Cache Hit Rate** | 0% | ≥60% | ≥50% |
| **Error Rate** | ~2% | ≤1.5% | ≤2% |
| **Retry Success Rate** | N/A | ≥95% | ≥90% |
| **Negative-Cycle Detection** | ✗ (crash/hang) | ✓ (error code) | 100% detection |
| **Time-to-Recovery (rollback)** | N/A | <2 min | <5 min |

---

## Summary

**v2 Greenfield Design Pillars:**

1. **Correctness:** Algorithm selection + validation handle both non-negative and negative-weight graphs.
2. **Robustness:** Idempotency, retry, timeout, circuit-breaker, structured logging.
3. **Observability:** Every request traced with unique ID; JSON logs for analysis.
4. **Safety:** Dual-write shadowing, canary rollout, rollback procedure.
5. **Performance:** Cache-first for typical requests; Dijkstra default for speed.

**Next Steps:**
1. Implement v2 routing_v2.py (Bellman-Ford, validation, logging).
2. Create 10+ integration tests + test fixtures.
3. Run dual-write staging tests for 1 week.
4. Deploy to prod with 0% traffic; monitor logs.
5. Begin canary: 10% → 25% → 50% → 100% over 5 days.
