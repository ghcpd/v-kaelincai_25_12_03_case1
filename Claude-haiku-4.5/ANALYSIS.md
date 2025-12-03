# Logistics Routing System – Analysis & Root-Cause Investigation

**Date:** December 3, 2025  
**Scope:** Greenfield redesign of logistics routing module (v1 → v2)  
**Focus:** Negative-weight graph handling, robustness, and operational readiness

---

## 1. Clarification & Data Collection

### 1.1 Missing Data / Assumptions

| Category | Item | Status | Impact | Assumption |
|----------|------|--------|--------|-----------|
| **Scale** | QPS, graph size (nodes/edges) | Unknown | Design capacity | Assume: small-scale (100s of nodes), batch processing OK |
| **Traffic** | Request volume, concurrency model | Unknown | Thread-safety, queue depth | Assume: single-threaded batch or low-concurrency APIs |
| **Persistence** | Caching, state store, DB | Unknown | Design for stateless-first | Assume: no external persistence required for routing logic |
| **SLA/SLO** | Latency SLA, availability target | Unknown | Timeout/retry strategy | Assume: p99 < 1s, 99.9% availability acceptable |
| **Failure Modes** | How are timeouts, bad inputs handled? | Unknown | Error budget, fallback | Assume: defensive, explicit error codes, no silent failures |
| **Monitoring** | Logs, metrics, alerting | Unknown | Observability design | Assume: structured JSON logs, OpenTelemetry ready |

### 1.2 Data Collection Checklist

- [x] **Codebase** – graph.py, routing.py, test files reviewed
- [x] **Known Issues** – KNOWN_ISSUE.md analyzed
- [x] **Test Data** – graph_negative_weight.json examined
- [ ] **Production Logs** – N/A (greenfield scope)
- [ ] **Traffic Patterns** – N/A (assume typical batch)
- [ ] **DB Schemas** – N/A (stateless scope)
- [ ] **API Specifications** – Inferred from code and tests

---

## 2. Background Reconstruction (Legacy Model)

### 2.1 Business Context

**Core Domain:** Logistics route optimization for cost minimization.

**Primary Flow:**
1. Load a directed, weighted graph of nodes (locations) and edges (routes with associated costs).
2. Compute shortest path from origin to destination.
3. Return optimized route and total cost.

**Key Assumptions:**
- Weights represent transit time, fuel cost, or distance.
- Graph is static per request (no real-time updates).
- Single origin-to-destination query per call.

### 2.2 System Boundaries

**Responsibilities:**
- Graph persistence (JSON file format)
- Shortest-path computation
- Path reconstruction

**Out of Scope:**
- Vehicle dispatch
- Real-time traffic/weather adjustments
- Multi-hop optimization (Vehicle Routing Problem)
- Load balancing or resource constraints

### 2.3 Dependencies & Integration Points

- **Input:** JSON-serialized directed graph
- **Output:** List of nodes (path) + total cost
- **Exception Handling:** Currently minimal; errors raise `ValueError`

---

## 3. Current-State Scan & Root-Cause Analysis

### 3.1 Symptoms & Issues Table

| Category | Symptom | Likely Root Cause | Evidence | Needed Evidence |
|----------|---------|-------------------|----------|-----------------|
| **Correctness** | Returns non-optimal path (A→B cost 5 vs A→C→D→F→B cost 1) | Dijkstra used on graph with negative edge; no input validation | graph_negative_weight.json, test_routing_negative_weight.py test failures | Stack trace from failing test |
| **Maintainability** | Comments state "intentional bugs"; unclear whether validation or algorithm choice is primary fix | Design intent ambiguous; no specification for handling negative edges | KNOWN_ISSUE.md lists both validation + algorithm as options | PM clarification on SLA expectations |
| **Reliability** | No graceful error for invalid graphs; crash-prone | Missing precondition checks (negative weights, disconnected graphs, self-loops) | routing.py line 14: no edge weight validation | Audit against graph invariants |
| **Observability** | No structured logging; no request IDs | Logging is print-free; no correlation across calls | src/logistics/routing.py – silent execution | Add request context + timing logs |
| **Testing** | Only 2 test cases; no edge cases (self-loops, zero weights, large graphs, disconnected nodes) | Limited test coverage; no performance/stress tests | tests/test_routing_negative_weight.py | Generate 5+ integration test scenarios |

### 3.2 Root-Cause Chains

#### **Issue #1: Dijkstra on Negative Weights**

**Hypothesis Chain:**
1. **Precondition Violation:** Graph contains edge with weight < 0 (D→F = -3).
2. **Algorithm Mismatch:** Dijkstra assumes non-negative weights; correctness theorem fails.
3. **Implementation Compounding:** Nodes marked visited upon discovery (line 37 in routing.py), preventing later relaxations.
4. **Result:** Path A→B (cost 5) returned; optimal path A→C→D→F→B (cost 1) never explored.

**Validation Method:**
```
Precondition: Run scan_graph(graph) for negative edges.
  If edge.weight < 0:
    - Reject with ValueError("Negative weight detected: {edge}"), OR
    - Invoke Bellman-Ford instead of Dijkstra.
Test: Run on graph_negative_weight.json; verify rejection or correct result (cost ≤ 1).
```

#### **Issue #2: Premature Visited Marking**

**Hypothesis Chain:**
1. **Visited Set Updated on Enqueue:** Line 37 adds node to `visited` when it is first discovered.
2. **Standard Dijkstra:** Should finalize node only when popped from heap with the smallest cost.
3. **Effect:** Once A→B→X is discovered, even if A→C→X later yields lower cost, X is skipped (line 30-31).
4. **Example:** Even with non-negative weights, A→E→B (7) might be visited before A→C→D→F→B (1) if E→B is discovered first.

**Validation Method:**
```
Precondition: Non-negative weights only.
Test: Ensure heap-based ordering is respected.
  - Remove `visited.add(neighbor)` from line 37.
  - Add visited check only at line 24: `if node in visited: continue`.
Test: Rerun test_dijkstra_finds_optimal_path_despite_negative_edge (expected cost = 1).
```

---

## 4. New-System Design (Greenfield v2)

### 4.1 Capability Boundaries & Service Decomposition

**New Scope:**
- Unified shortest-path service supporting both non-negative (Dijkstra) and negative-weight (Bellman-Ford) graphs.
- Explicit validation and rejection of invalid graphs (negative cycles, disconnected nodes).
- Robust error handling, idempotency, and structured logging.
- Observability-first: every request traced with unique IDs, timing, and outcome metadata.

**Service Contract (v2 API):**

```python
def compute_shortest_path(
    graph: Graph,
    start: str,
    goal: str,
    request_id: str = None,  # For tracing & idempotency
    config: RoutingConfig = None  # Timeout, retry policy
) -> RoutingResult:
    """
    Compute shortest path from start to goal.
    
    Args:
        graph: Directed weighted graph (may contain negative edges).
        start: Start node identifier.
        goal: Goal node identifier.
        request_id: Unique request identifier for audit/idempotency.
        config: Routing configuration (timeouts, algorithm selection).
    
    Returns:
        RoutingResult(
            path: List[str],
            cost: float,
            algorithm: str ("dijkstra" | "bellman_ford"),
            request_id: str,
            duration_ms: float,
            status: str ("success" | "error"),
            error_code: str | None
        )
    
    Raises:
        ValidationError: If graph is invalid (negative cycle, disconnected nodes).
        TimeoutError: If computation exceeds config.timeout_ms.
        NodeNotFoundError: If start or goal not in graph.
    """
```

### 4.2 State Machine & Idempotency Strategy

**Request Lifecycle:**

```
┌─────────────────────────────────────────────────────────────────┐
│ INCOMING REQUEST (request_id, graph, start, goal)              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────┐
        │ CHECK IDEMPOTENCY CACHE          │
        │ (request_id → cached_result?)    │
        └───┬──────────────────────────────┘
            │ HIT         │ MISS
            │             ▼
            │    ┌────────────────────────────────────┐
            │    │ VALIDATE INPUT                     │
            │    │ • Node exists (start, goal)?       │
            │    │ • Graph non-empty?                 │
            │    │ • No negative cycle?               │
            │    └───┬────────────────┬───────────────┘
            │        │ VALID          │ INVALID
            │        ▼                ▼
            │    ┌─────────────────┐ ┌──────────────────────────┐
            │    │ SCAN GRAPH      │ │ LOG ERROR & REJECT       │
            │    │ • Detect        │ │ • error_code: VAL_*      │
            │    │   negative edge?│ │ • status: error          │
            │    └───┬─────────────┘ └──────────────────────────┘
            │        │               │ Idempotent: cache error
            │        ▼               ▼ for retry deduplication
            │    ┌──────────────────────────────────┐
            │    │ CHOOSE ALGORITHM                 │
            │    │ neg_edge? → Bellman-Ford         │
            │    │ else      → Dijkstra (faster)    │
            │    └───┬──────────────┬────────────────┘
            │        │              │ TIMEOUT
            │        ▼              ▼
            │    ┌────────────────┐ ┌──────────────────────────┐
            │    │ COMPUTE PATH   │ │ TIMEOUT HANDLER          │
            │    │ + TIME EXEC    │ │ • error_code: TIMEOUT    │
            │    │ + LOG STRUCTURED│ │ • Partial result cache   │
            │    └───┬──────────────┘ └──────────────────────────┘
            │        │ SUCCESS        │ LOG & RETURN
            │        ▼                ▼
            │    ┌──────────────────────────────────┐
            │    │ BUILD RESULT                     │
            │    │ • path, cost, algorithm, timing  │
            │    │ • CACHE for idempotency          │
            │    │ • LOG SUCCESS                    │
            │    └───┬──────────────────────────────┘
            │        │
            ▼        ▼
        ┌──────────────────────────────────────────┐
        │ RETURN RESULT                            │
        │ (status, path, cost, request_id, timing) │
        └──────────────────────────────────────────┘
```

**Idempotency Key Design:**
- **Idempotency Key:** `SHA256(graph_hash + start + goal)` or explicit `request_id` parameter.
- **Cache:** In-memory dict `{request_id → RoutingResult}` with TTL (e.g., 5 min).
- **Semantics:** Exact same request always returns the same result, even if retried.
- **Garbage Collection:** Evict cache entries older than TTL on background or access.

### 4.3 Robustness Strategies

#### **Retry with Exponential Backoff**

```python
class RetryPolicy:
    max_retries: int = 3
    initial_delay_ms: int = 100
    backoff_multiplier: float = 2.0
    max_delay_ms: int = 5000

def with_retry(
    func: Callable,
    policy: RetryPolicy = RetryPolicy(),
    jitter: bool = True
) -> Any:
    """Invoke func with exponential backoff; return result or raise final error."""
    for attempt in range(policy.max_retries):
        try:
            result = func()
            if attempt > 0:
                log_retry_success(attempt)
            return result
        except Exception as e:
            if attempt == policy.max_retries - 1:
                log_retry_exhausted(e)
                raise
            delay = policy.initial_delay_ms * (policy.backoff_multiplier ** attempt)
            if jitter:
                delay = delay * (0.5 + random.random())
            delay = min(delay, policy.max_delay_ms)
            log_retry_attempt(attempt, delay, e)
            time.sleep(delay / 1000.0)
```

#### **Timeout Propagation**

```python
class RoutingConfig:
    timeout_ms: int = 1000
    algorithm_hint: str = "auto"  # "dijkstra" | "bellman_ford" | "auto"

def compute_shortest_path_with_timeout(
    graph: Graph,
    start: str,
    goal: str,
    config: RoutingConfig = RoutingConfig()
) -> RoutingResult:
    """Wrap algorithm with timeout; interrupt and return partial result on timeout."""
    import signal
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Routing computation exceeded {config.timeout_ms}ms")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(config.timeout_ms // 1000 + 1)  # Approximate ceiling
    
    try:
        start_time = time.time()
        result = _compute_path(graph, start, goal, config)
        elapsed_ms = (time.time() - start_time) * 1000
        result.duration_ms = elapsed_ms
        return result
    except TimeoutError as e:
        elapsed_ms = (time.time() - start_time) * 1000
        log_warning(f"Routing timeout: {elapsed_ms}ms / {config.timeout_ms}ms", request_id=request_id)
        return RoutingResult(
            path=None,
            cost=None,
            status="error",
            error_code="TIMEOUT",
            error_message=str(e),
            duration_ms=elapsed_ms,
            request_id=request_id
        )
    finally:
        signal.alarm(0)  # Cancel alarm
```

#### **Circuit Breaker (Optional, for Distributed Scenarios)**

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Reject fast
    HALF_OPEN = "half_open"  # Test recovery

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout_sec: int = 60):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout_sec = timeout_sec
        self.last_failure_time = None
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout_sec):
                self.state = CircuitState.HALF_OPEN
                self.failure_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
            raise
```

### 4.4 Structured Logging & Audit Schema

**Log Entry Structure (JSON):**

```json
{
  "timestamp": "2025-12-03T10:15:30.123Z",
  "request_id": "req_abc123xyz",
  "event_type": "routing_request|routing_success|routing_error|routing_timeout|retry_attempt",
  "level": "INFO|WARN|ERROR",
  "service": "logistics-routing-v2",
  "user_id": "user_123",
  "graph_hash": "sha256(edges)",
  "start_node": "A",
  "goal_node": "B",
  "algorithm_selected": "dijkstra|bellman_ford|error",
  "path": ["A", "C", "D", "F", "B"],
  "cost": 1.0,
  "duration_ms": 42.5,
  "error_code": null,
  "error_message": null,
  "retry_attempt": 0,
  "cache_hit": true,
  "graph_validation": {
    "node_count": 6,
    "edge_count": 7,
    "has_negative_weights": true,
    "has_negative_cycle": false,
    "is_connected": false
  },
  "metadata": {
    "client_version": "v2.0.0",
    "timeout_ms": 1000,
    "sensitive_fields_masked": true
  }
}
```

**Masked Sensitive Fields:** Node names can be hashed or abbreviated in production logs; full paths logged only to secure audit store.

### 4.5 Algorithm Selection & Validation

**Decision Tree:**

```
┌─ validate_graph(graph) ─────────────────────────────────────────────┐
│                                                                       │
│  1. Nodes in graph?                 ─NO─> ERROR: EMPTY_GRAPH        │
│     │                                                                │
│     YES                                                             │
│     │                                                                │
│  2. Start & goal nodes exist?       ─NO─> ERROR: NODE_NOT_FOUND     │
│     │                                                                │
│     YES                                                             │
│     │                                                                │
│  3. Any self-loops (u → u)?         ─YES─> WARNING: IGNORED         │
│     │                                                                │
│     │                                                                │
│  4. Scan for negative weights       ─YES─> Check for cycle...       │
│     │                              │                               │
│     NO                             ▼                               │
│     │                    Has negative cycle? ─YES─> ERROR: NEG_CYCLE
│     │                              │                               │
│     └──────────────────────────────NO────────────────────┐          │
│                                    ▼                    │          │
│            Has negative weights? ─YES─> Use Bellman-Ford│          │
│                                    │                    │          │
│                                    NO                   │          │
│                                    │                    │          │
│                                    └──────┬─────────────┘          │
│                                           ▼                        │
│                                  Use Dijkstra (faster)            │
└───────────────────────────────────────────────────────────────────┘
```

**Bellman-Ford for Negative Weights:**

```python
def bellman_ford_shortest_path(
    graph: Graph,
    start: str,
    goal: str,
    request_id: str = None
) -> Tuple[List[str], float]:
    """
    Compute shortest path in graph with negative edges (no negative cycles).
    
    Algorithm:
      1. Initialize dist[start] = 0, dist[all_others] = ∞.
      2. Relax edges |V|-1 times.
      3. Check for negative cycles.
      4. Reconstruct path.
    
    Time: O(|V| * |E|)
    Space: O(|V|)
    """
    dist = {node: float("inf") for node in graph.nodes()}
    dist[start] = 0.0
    prev = {node: None for node in graph.nodes()}
    
    # Relax edges |V|-1 times
    for _ in range(len(dist) - 1):
        updated = False
        for u in graph.nodes():
            if dist[u] == float("inf"):
                continue
            for v, weight in graph.neighbors(u).items():
                if dist[u] + weight < dist[v]:
                    dist[v] = dist[u] + weight
                    prev[v] = u
                    updated = True
        if not updated:
            break  # Early exit if no updates
    
    # Check for negative cycles
    for u in graph.nodes():
        if dist[u] == float("inf"):
            continue
        for v, weight in graph.neighbors(u).items():
            if dist[u] + weight < dist[v]:
                raise ValueError(f"Negative cycle detected reachable from {start}")
    
    if dist[goal] == float("inf"):
        raise ValueError(f"No path found from {start} to {goal}")
    
    return _reconstruct_path(prev, goal), dist[goal]
```

---

## 5. Migration & Parallel Run Strategy

### 5.1 Read-Write Cutover

**Phase 1: Dual-Write (Shadowing)**
- v1 computes route and returns to caller (primary).
- v2 computes route in parallel (shadow); log results for comparison.
- No caller sees v2 result; used only for validation.
- Duration: 1–2 weeks; collect metrics on correctness, latency, errors.

**Phase 2: Canary Switch (10% → 100%)**
- v2 now primary for 10% of requests (e.g., by request_id hash).
- v1 still shadows for validation.
- Monitor error rates, latency p99, cache hit rates.
- Increment canary by 25% daily if metrics green.

**Phase 3: Rollback Path**
- If v2 error rate > 5% or p99 latency > 2× baseline: immediate rollback to v1 only.
- Keep both versions deployed for 30 days post-cutover for safe rollback.
- Idempotency keys ensure requests retried on v1 return same result.

### 5.2 Backfill & Historical Reconciliation

**Not applicable** for stateless routing service (no persistent state to migrate).

### 5.3 Rollback Procedure

```bash
# If v2 shows elevated errors:
1. Toggle feature flag: ROUTING_V2_ENABLED=false
2. Clear v2 cache: redis-cli FLUSHDB --async  # if using Redis
3. Revert code: git revert <commit_hash>
4. Redeploy: kubectl rollout undo deployment/routing-service -n logistics
5. Alert on-call; create incident post-mortem.
6. Keep v2 binary in registry for investigation.
```

---

## 6. Testing & Acceptance Criteria

### 6.1 Integration Test Cases (Derived from Crash Points)

| Test ID | Target Issue | Preconditions | Steps | Expected Outcome | Observability |
|---------|--------------|---------------|-------|-------------------|-----------------|
| **TC-001** | Normal path (non-negative) | Graph: A→B(5), A→C(2), C→D(1), D→B(1) | Compute A→B | Path: A→C→D→B, Cost: 4.0 | duration_ms < 100, algorithm: dijkstra |
| **TC-002** | Negative-weight rejection | Graph: A→B(5), B→C(-3) | Compute A→C | Status: success, algorithm: bellman_ford, cost: 2.0 | No error; Bellman-Ford selected |
| **TC-003** | Negative-cycle detection | Graph: A→B(-1), B→C(-1), C→A(-1) | Compute A→C | Status: error, error_code: NEG_CYCLE | Log: "Negative cycle detected" |
| **TC-004** | Idempotency (cache hit) | Same request_id repeated | Call twice with same request_id | 2nd call returns cached result | cache_hit: true on 2nd call, duration_ms ≈ 1ms |
| **TC-005** | Retry with backoff | Service temporarily fails then recovers | Inject transient failure; retry 3x | Succeeds on 2nd retry attempt | retry_attempt: 1, backoff_delay_ms logs |
| **TC-006** | Timeout propagation | Large graph, config.timeout_ms=100 | Compute path in large graph | Status: error, error_code: TIMEOUT | duration_ms ≈ 100, timeout_triggered: true |
| **TC-007** | Node not found | start_node not in graph | Compute A→Z (Z not in graph) | Status: error, error_code: NODE_NOT_FOUND | Log: "goal node Z not in graph" |
| **TC-008** | Empty graph | Graph with no edges | Compute A→B | Status: error, error_code: EMPTY_GRAPH | Validation catches at precondition |
| **TC-009** | Concurrent requests (thread-safe) | 10 concurrent requests, same graph | Fire 10 requests in parallel | All 10 succeed; no race conditions | request_id unique per call, no cross-contamination |
| **TC-010** | Audit trail completeness | Any routing request | Log all steps (validation, algorithm selection, result) | All events logged with request_id | Structured JSON logs; request_id correlation ✓ |

### 6.2 Acceptance Criteria (Given-When-Then)

**AC-001: Correctness**
```
Given a graph with negative edges but no negative cycles,
When I call compute_shortest_path(graph, "A", "B"),
Then the result path has cost ≤ any alternative path,
 AND the algorithm selected is "bellman_ford",
 AND status is "success".
```

**AC-002: Negative-Cycle Detection**
```
Given a graph with a negative cycle,
When I call compute_shortest_path(graph, start, goal),
Then status is "error" AND error_code is "NEG_CYCLE",
 AND no infinite loops occur in the algorithm.
```

**AC-003: Idempotency**
```
Given two identical requests with the same request_id,
When I call compute_shortest_path for both,
Then both return identical results,
 AND the second call is served from cache with duration_ms < 2ms,
 AND no duplicate side effects (logs, metrics) are counted.
```

**AC-004: Timeout**
```
Given a large graph and timeout_ms=100,
When compute_shortest_path is called,
Then if computation exceeds 100ms, the call returns error_code="TIMEOUT",
 AND actual duration_ms ≤ 110ms (with 10ms margin),
 AND partial/stale result is not returned.
```

**AC-005: Latency SLO**
```
Given typical workloads (small-to-medium graphs, non-negative weights),
When 100 sequential requests are executed,
Then p50 latency ≤ 10ms, p99 ≤ 50ms,
 AND cache hit rate ≥ 60% for identical requests.
```

---

## 7. Risk & Uncertainty Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| Bellman-Ford slower than expected on large graphs | p99 latency > 2s | Medium | Benchmark on target graph sizes; add algorithm hint config; consider approximation algorithms |
| Thread-safety issues under concurrency | Data corruption, inconsistent results | Low | Use immutable Graph; protect idempotency cache with locks; unit test with ThreadPoolExecutor |
| Negative cycle detection misses cycles | Silent infinite loop | Low | Unit test with all known negative-cycle graphs; peer review algorithm |
| Idempotency cache grows unbounded | Memory leak | Medium | Implement TTL eviction; periodic cleanup; monitor cache size; set hard limits |
| Timeout handler (signal.alarm) not portable across OS | Breaks on Windows | High | Replace with threading.Timer; use concurrent.futures.TimeoutError instead |
| Logs too verbose in production | Disk I/O bottleneck | Medium | Use log levels; sample debug logs; async I/O logging |

---

## 8. Unknowns & Recommendations

### 8.1 Open Questions for Stakeholders

1. **Graph Scale:** What is the max number of nodes/edges in a typical request? (Affects algorithm choice and timeout tuning.)
2. **SLA/SLO:** What is the target p99 latency and availability % for routing?
3. **Negative-Weight Semantics:** When would negative weights occur in practice? (Discounts, speed bonuses?) Should they be rejected by business logic or allowed?
4. **Deployment Environment:** Single-thread batch, async workers, or distributed microservice? (Affects retry/circuit-breaker design.)
5. **Monitoring & Alerting:** Do you have a centralized logging system (e.g., ELK, Datadog)? How should alerts be configured?

### 8.2 Recommended Next Steps

1. **Benchmark Bellman-Ford** on target graph sizes (measure latency, memory).
2. **Run dual-write test** (v1 shadow + v2 primary) on staging for 1 week.
3. **Set concrete SLAs** (latency, availability, error budget).
4. **Plan rollout:** feature flag, canary percentages, monitoring dashboard.
5. **Load test:** concurrent requests, large graphs, timeout edge cases.

---

## Summary

**Legacy Issue:** v1 runs Dijkstra on graphs with negative weights, producing incorrect results due to missing validation and premature visited marking.

**Root Causes:**
1. No negative-edge detection before algorithm invocation.
2. Nodes marked visited on discovery, not finalization, preventing later relaxations.

**v2 Solution:**
1. Unified algorithm selection (Dijkstra for non-negative; Bellman-Ford for negative).
2. Explicit negative-cycle detection and validation.
3. Idempotency keys, retry with backoff, timeout propagation, structured logging.
4. Comprehensive integration tests (10 scenarios covering normal, error, performance paths).
5. Dual-write shadowing, canary rollout, rollback procedures.

**Success Metrics:**
- Correctness: 100% match to expected path costs on all test cases.
- Idempotency: Cache hit rate ≥ 60%; cached results served in < 2ms.
- Latency: p99 < 50ms for typical graphs; p99 < 200ms for large graphs.
- Reliability: Error rate < 1%; no silent failures; all requests traced.
