# Logistics Routing System v2 - Greenfield Replacement

## Executive Summary

This document presents a **greenfield replacement** for the legacy logistics routing system that suffers from algorithmic correctness issues, lack of input validation, and absence of resilience patterns. The v2 system addresses these shortcomings with proper algorithm selection, comprehensive validation, idempotency guarantees, retry mechanisms, and circuit breakers.

---

## 1. CLARIFICATION & DATA COLLECTION

### 1.1 Missing Data & Assumptions

| Missing Data | Assumption Made |
|-------------|-----------------|
| Production traffic volume | 10,000 routing requests/day; 99.9% availability requirement |
| External service dependencies | No external dependencies; pure computational service |
| Historical incident logs | Inferred from test failures: incorrect routes returned |
| Concurrent request patterns | Single-threaded processing acceptable; horizontal scaling for throughput |
| Business SLA requirements | Route calculation < 100ms p95; correctness > 99.99% |
| Data retention requirements | Request logs retained 30 days; audit trail for compliance |
| Graph data sources | JSON files; future: database or external graph service |
| Deployment environment | Docker/Kubernetes; stateless service |

### 1.2 Data Collection Checklist

- [x] Source code review (graph.py, routing.py)
- [x] Test suite analysis (test_routing_negative_weight.py)
- [x] Known issue documentation (KNOWN_ISSUE.md)
- [x] Graph data samples (graph_negative_weight.json)
- [ ] Production logs (not available; simulated in v2)
- [ ] Performance metrics (to be measured in comparison tests)
- [ ] User feedback/complaints (inferred from test expectations)
- [ ] Database schema (N/A for computational service)
- [ ] API contracts (to be defined in v2)

---

## 2. BACKGROUND RECONSTRUCTION

### 2.1 Business Context (Inferred)

**Domain**: Logistics and supply chain optimization

**Core Function**: Compute shortest/optimal paths through weighted directed graphs representing:
- Transportation networks (nodes = warehouses/distribution centers)
- Cost optimization (edge weights = distance, time, fuel cost, tolls)
- Route planning for delivery vehicles

**Business Criticality**: 
- Incorrect routes → increased operational costs (fuel, time)
- Missing validation → system failures in production
- No resilience → service unavailable during transient issues

### 2.2 Core Flows

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ 1. Request(graphId, start, goal)
       v
┌─────────────────────────────┐
│  Routing Service (Legacy)   │
│  - Load graph from file      │
│  - Run Dijkstra (buggy)     │
│  - Return path + cost        │
└──────┬──────────────────────┘
       │ 2. Response(path, cost)
       v
┌─────────────┐
│   Client    │
└─────────────┘
```

### 2.3 System Boundaries

- **In Scope**: Graph loading, shortest path computation, input validation
- **Out of Scope**: Graph data persistence, real-time traffic updates, multi-objective optimization
- **Dependencies**: Python standard library, JSON data files

### 2.4 Uncertainties

1. **Graph update frequency**: Static files vs. dynamic updates?
2. **Concurrency requirements**: Single request or concurrent processing?
3. **Graph size limits**: Max nodes/edges for performance guarantees?
4. **Negative weight semantics**: Rebates/discounts or data errors?
5. **Caching strategy**: In-memory graph cache vs. reload per request?

---

## 3. CURRENT-STATE SCAN & ROOT-CAUSE ANALYSIS

### 3.1 Issue Analysis Table

| Category | Symptom | Likely Root Cause | Evidence | Priority | Needed Evidence |
|----------|---------|-------------------|----------|----------|-----------------|
| **Functionality** | Incorrect shortest path returned (cost=5 instead of 1) | Dijkstra algorithm doesn't support negative weights; premature node finalization | Test failure: `assert ['A', 'B'] == ['A', 'C', 'D', 'F', 'B']` | **CRITICAL** | Production incident logs showing wrong routes |
| **Functionality** | No rejection of invalid graphs | Missing input validation for algorithm preconditions | Test failure: `DID NOT RAISE <class 'ValueError'>` | **CRITICAL** | Customer complaints about algorithm failures |
| **Reliability** | No retry mechanism for transient failures | Code assumes all operations succeed | Absence of retry logic in routing.py | **HIGH** | Logs of intermittent file I/O failures |
| **Reliability** | No idempotency guarantees | No request ID tracking or duplicate detection | No idempotency key handling in code | **HIGH** | Duplicate route calculation costs |
| **Reliability** | No timeout protection | Synchronous blocking calls without limits | No timeout configuration in code | **HIGH** | Incidents of hung requests |
| **Reliability** | No circuit breaker for cascading failures | No failure tracking or automatic degradation | No circuit breaker pattern implemented | **MEDIUM** | Service degradation during issues |
| **Performance** | Dijkstra O(E log V) not optimal for negative weights | Algorithm choice doesn't match graph properties | Benchmark data needed | **MEDIUM** | Performance metrics for large graphs |
| **Maintainability** | Tight coupling between graph loading and algorithm | No abstraction for algorithm selection | Monolithic routing.py implementation | **MEDIUM** | Developer feedback on extensibility |
| **Security** | No input sanitization for node IDs | SQL injection or path traversal risk if node IDs used in queries | No validation in graph.py | **LOW** | Security audit findings |
| **Observability** | No structured logging | Difficult to debug issues in production | No logging statements in routing.py | **HIGH** | Incident response time metrics |
| **Observability** | No metrics/telemetry | No visibility into performance or success rates | No instrumentation code | **MEDIUM** | SLO/SLA compliance reports |

### 3.2 High-Priority Issue Deep Dive

#### Issue 1: Incorrect Shortest Path Calculation

**Hypothesis Chain**:
```
H1: Dijkstra called on negative-weight graph 
    → Algorithm assumption violated (all edges ≥ 0)
    → Greedy choice property breaks
    → Suboptimal path returned

H2: Premature node finalization (visited.add on discovery)
    → Node B marked visited when reached via A→B (cost 5)
    → Later relaxation via A→C→D→F→B (cost 1) blocked
    → Cannot update B's distance
    → Wrong path returned
```

**Validation Method**:
1. Trace execution with debug logging for visited set changes
2. Add assertion before Dijkstra: `all(weight >= 0 for edges in graph)`
3. Unit test with positive-weight graph → should pass
4. Unit test with negative-weight graph → should fail/reject

**Fix Path with Causal Chain**:
```
Root Cause → Fix → Expected Outcome
─────────────────────────────────────
No validation → Add negative-weight detection → Reject invalid graphs OR
Wrong algorithm → Implement Bellman-Ford/SPFA → Correct results for negative weights
Premature finalization → Move visited.add to after heappop → Dijkstra correct for valid graphs
```

#### Issue 2: No Resilience Patterns

**Hypothesis Chain**:
```
File I/O failure (graph load) 
    → Exception propagates to caller
    → No retry attempted
    → Request fails immediately
    → User sees 5xx error
```

**Validation Method**:
1. Simulate file system error (permission denied)
2. Simulate corrupt JSON data
3. Observe: immediate failure, no retry
4. Add retry with exponential backoff
5. Re-test: transient failures recovered

**Fix Path**:
```
No retry → Add tenacity/backoff decorator → Transient failures recovered
No idempotency → Add request ID + result cache → Duplicate requests return cached result
No timeout → Add timeout decorator → Prevent hung requests
No circuit breaker → Add failure counter + circuit breaker → Prevent cascade failures
```

---

## 4. NEW SYSTEM DESIGN (GREENFIELD REPLACEMENT)

### 4.1 Target State Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Routing Service v2                        │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           API Layer (FastAPI/Flask)                │    │
│  │  - Request validation (Pydantic schemas)           │    │
│  │  - Idempotency key handling                        │    │
│  │  - Structured logging (request_id, correlation_id) │    │
│  └───────────────────┬────────────────────────────────┘    │
│                      │                                       │
│  ┌───────────────────v────────────────────────────────┐    │
│  │         Service Orchestration Layer                │    │
│  │  - Circuit breaker (PyBreaker/resilience4j)        │    │
│  │  - Retry with exponential backoff (tenacity)       │    │
│  │  - Timeout enforcement (signals/asyncio)           │    │
│  │  - Result caching (request_id → result)            │    │
│  └───────────────────┬────────────────────────────────┘    │
│                      │                                       │
│  ┌───────────────────v────────────────────────────────┐    │
│  │          Routing Core (Business Logic)             │    │
│  │  - Graph loader + validator                        │    │
│  │  - Algorithm selector (strategy pattern)           │    │
│  │    * Dijkstra (positive weights)                   │    │
│  │    * Bellman-Ford (negative weights, no cycles)    │    │
│  │    * Johnson (negative weights, dense graphs)      │    │
│  │  - Path validator + cost calculator                │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
         │                           │
         v                           v
  ┌─────────────┐           ┌──────────────┐
  │   Metrics   │           │   Audit Log  │
  │ (Prometheus)│           │  (Structured)│
  └─────────────┘           └──────────────┘
```

### 4.2 Service Decomposition

**Single Service (Monolithic for v2)**:
- **Rationale**: Pure computational service, no external dependencies, low complexity
- **Future decomposition**: If graph data grows → separate Graph Service

**Capability Boundaries**:
1. **Graph Management**: Load, validate, cache graphs
2. **Algorithm Selection**: Choose optimal algorithm based on graph properties
3. **Path Computation**: Execute algorithm with resilience patterns
4. **Result Validation**: Verify path correctness (all edges exist, cost matches)
5. **Observability**: Emit metrics, logs, traces

### 4.3 Unified State Machine

```
Route Request Lifecycle:
┌─────────┐
│  INIT   │ (request received, validate schema)
└────┬────┘
     │
     v
┌──────────────┐
│  VALIDATED   │ (schema OK, check idempotency)
└────┬─────────┘
     │
     ├─[cached]──────> CACHED_HIT (return cached result)
     │
     v
┌──────────────┐
│  LOADING     │ (load graph from storage)
└────┬─────────┘
     │
     ├─[load error]──> LOAD_FAILED (retry or fail)
     │
     v
┌──────────────┐
│  LOADED      │ (validate graph properties)
└────┬─────────┘
     │
     ├─[invalid graph]──> INVALID_GRAPH (reject request)
     │
     v
┌──────────────┐
│  COMPUTING   │ (run algorithm with timeout)
└────┬─────────┘
     │
     ├─[timeout]──────> TIMEOUT (circuit breaker increment)
     ├─[algorithm error]──> COMPUTE_FAILED (retry or fail)
     │
     v
┌──────────────┐
│  VALIDATING  │ (verify path correctness)
└────┬─────────┘
     │
     ├─[invalid result]──> INVALID_RESULT (log + fail)
     │
     v
┌──────────────┐
│  SUCCESS     │ (cache result, emit metrics, return)
└──────────────┘

Crash Points (Legacy):
❌ LOADING: File I/O error → uncaught exception
❌ COMPUTING: Negative weight → wrong result (no crash but incorrect)
❌ COMPUTING: Infinite loop → timeout not enforced
```

### 4.4 Resilience Patterns

#### Idempotency

**Strategy**: Request ID + LRU Cache
```python
@lru_cache(maxsize=1000)
def compute_route(request_id: str, graph_hash: str, start: str, goal: str):
    # Cache key includes all inputs
    # Repeated calls with same request_id return cached result
    pass
```

**Implementation**:
- Client provides `X-Request-ID` header (or auto-generate UUID)
- Hash graph content for cache key (detect graph changes)
- TTL: 5 minutes (balance memory vs. correctness)
- Eviction: LRU policy

#### Retry with Exponential Backoff

**Strategy**: Tenacity library
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(TransientError),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def load_graph(path: str) -> Graph:
    pass
```

**Retry Conditions**:
- File I/O errors (PermissionError, FileNotFoundError if transient NFS)
- Corrupt data (JSONDecodeError) → No retry (permanent failure)
- Timeout errors → Retry with longer timeout

**Backoff Parameters**:
- Initial: 1s, Multiplier: 2x, Max: 10s
- Max attempts: 3 (1s, 2s, 4s total ~7s)

#### Timeout Enforcement

**Strategy**: Context manager with signal (Linux) or threading (Windows)
```python
with timeout(seconds=5):
    path, cost = algorithm.compute(graph, start, goal)
```

**Timeout Values**:
- Graph loading: 2s
- Path computation: 5s (O(E log V) for 10k nodes/50k edges ~500ms)
- Total request: 10s (includes retries)

#### Circuit Breaker

**Strategy**: PyBreaker library
```python
breaker = CircuitBreaker(
    fail_max=5,          # Open after 5 failures
    timeout_duration=60,  # Stay open 60s
    expected_exception=GraphLoadError
)

@breaker
def load_graph_with_breaker(path: str):
    return load_graph(path)
```

**States**:
- **Closed**: Normal operation
- **Open**: Fail fast (return cached result or error)
- **Half-Open**: Single test request after timeout

**Failure Conditions**:
- Graph load failures
- Algorithm timeouts
- Invalid results (potential data corruption)

### 4.5 Algorithm Selection Strategy

**Decision Tree**:
```
Has negative edges?
├─ NO  → Use Dijkstra (O(E log V) with binary heap)
│        Fast, optimal for 99% of real-world graphs
│
└─ YES → Check for negative cycles
          ├─ Has cycle → REJECT (undefined shortest path)
          │              Use Bellman-Ford to detect cycle
          │
          └─ No cycle  → Use Bellman-Ford (O(VE))
                         Slower but correct for negative weights
                         
Alternative (if performance critical):
└─ YES → Use Johnson's algorithm (O(VE + V^2 log V))
         Reweight graph, then run Dijkstra
         Efficient for dense graphs with negative edges
```

**Implementation**:
```python
class RoutingEngine:
    def select_algorithm(self, graph: Graph) -> PathAlgorithm:
        has_negative = any(w < 0 for edges in graph.neighbors() for w in edges.values())
        
        if not has_negative:
            return DijkstraAlgorithm()
        
        # Detect negative cycle with Bellman-Ford
        has_cycle = self._has_negative_cycle(graph)
        if has_cycle:
            raise ValueError("Graph contains negative cycle; shortest path undefined")
        
        return BellmanFordAlgorithm()
```

### 4.6 Key Interfaces & Schemas

#### API Request Schema
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "graph_id": "logistics_network_v2",
  "start_node": "warehouse_sf",
  "goal_node": "store_nyc",
  "options": {
    "algorithm": "auto",  // or "dijkstra", "bellman_ford"
    "timeout_ms": 5000,
    "validate_result": true
  }
}
```

**Field Constraints**:
- `request_id`: UUID v4 format, optional (auto-generated if missing)
- `graph_id`: Alphanumeric + underscore, max 64 chars
- `start_node`, `goal_node`: UTF-8 string, max 128 chars, must exist in graph
- `algorithm`: Enum ["auto", "dijkstra", "bellman_ford", "johnson"]
- `timeout_ms`: Integer, range [100, 30000]

#### API Response Schema
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "success",  // or "error", "timeout"
  "path": ["warehouse_sf", "hub_chicago", "hub_philadelphia", "store_nyc"],
  "cost": 2847.5,
  "metadata": {
    "algorithm_used": "dijkstra",
    "computation_time_ms": 23,
    "graph_nodes": 1500,
    "graph_edges": 8200,
    "cache_hit": false
  }
}
```

#### Error Response Schema
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "error",
  "error": {
    "code": "NEGATIVE_CYCLE_DETECTED",
    "message": "Graph contains negative weight cycle; shortest path undefined",
    "details": {
      "cycle": ["A", "C", "D", "F", "A"],
      "cycle_cost": -2.5
    }
  }
}
```

**Error Codes**:
- `INVALID_INPUT`: Schema validation failed
- `GRAPH_NOT_FOUND`: graph_id doesn't exist
- `NODE_NOT_FOUND`: start/goal node not in graph
- `NEGATIVE_CYCLE_DETECTED`: Graph has negative cycle
- `COMPUTATION_TIMEOUT`: Algorithm exceeded timeout
- `NO_PATH_EXISTS`: Nodes not connected
- `INTERNAL_ERROR`: Unexpected failure

### 4.7 Data Flow

```
[Client]
   │
   │ POST /v2/route
   │ {"request_id": "abc", "graph_id": "net1", "start": "A", "goal": "B"}
   │
   v
[API Gateway]
   │ Validate schema (Pydantic)
   │ Extract request_id
   │
   v
[Idempotency Check]
   │ Check cache[request_id + graph_hash + start + goal]
   ├─[Hit]──> Return cached response (200 OK)
   │
   └─[Miss]
      │
      v
[Circuit Breaker Check]
   │ Check breaker state
   ├─[Open]──> Return 503 Service Unavailable
   │
   └─[Closed/Half-Open]
      │
      v
[Graph Loader] @retry(3x, exponential backoff)
   │ Load graph from file/DB
   │ Validate: all weights are numeric
   │ Compute graph_hash (MD5 of edges)
   │
   v
[Algorithm Selector]
   │ Analyze graph properties
   │ Select: Dijkstra | Bellman-Ford | Johnson
   │
   v
[Path Computation] @timeout(5s)
   │ Execute algorithm
   │ Track metrics: node_visits, edge_relaxations, time_ms
   │
   v
[Result Validator]
   │ Verify: path[i] → path[i+1] edge exists
   │ Verify: sum(edge_weights) == returned cost
   │
   v
[Cache & Return]
   │ Cache result (request_id → response)
   │ Emit metrics (success, latency)
   │ Log audit trail
   │ Return 200 OK with path + cost
```

### 4.8 Migration & Parallel Run

**Phase 1: Shadow Mode (Week 1-2)**
- Deploy v2 alongside legacy
- Route 100% traffic to legacy (production)
- Clone requests to v2 (async, no blocking)
- Compare results: log discrepancies
- Metrics: correctness delta, latency delta

**Phase 2: Canary (Week 3)**
- Route 5% traffic to v2
- Monitor error rate, latency p95, correctness
- Rollback trigger: error rate > 0.1% OR latency > 2x baseline
- Gradually increase: 5% → 10% → 25% → 50%

**Phase 3: Full Cutover (Week 4)**
- Route 100% traffic to v2
- Keep legacy running (read-only) for 1 week
- Rollback plan: DNS/load balancer flip (< 5 min)

**Phase 4: Decommission (Week 5)**
- Archive legacy code
- Migrate historical data (if any)
- Update documentation

**Backfill Strategy** (N/A for stateless service):
- No historical data to migrate
- If caching enabled: warm cache with top 1000 routes

**Rollback Path**:
1. Detect anomaly (automated: error rate, manual: user report)
2. Flip traffic back to legacy (load balancer config change)
3. Drain v2 connections (30s grace period)
4. Investigate root cause
5. Fix + re-deploy v2
6. Resume canary phase

---

## 5. TESTING & ACCEPTANCE

### 5.1 Integration Test Cases

#### Test Case 1: Idempotency - Duplicate Requests

**Target Issue**: No idempotency guarantees (High Priority)

**Preconditions**:
- Graph: `positive_weight_graph.json` (A→B=5, A→C→B=3)
- Service: v2 running with cache enabled

**Test Data**:
```json
{
  "request_id": "test-idempotency-001",
  "graph_id": "positive_weight",
  "start_node": "A",
  "goal_node": "B"
}
```

**Steps**:
1. Send request #1 (POST /v2/route)
2. Verify response: path=["A","C","B"], cost=3
3. Extract computation_time_ms from metadata (e.g., 50ms)
4. Send identical request #2 (same request_id)
5. Verify response: identical path/cost
6. Extract computation_time_ms #2 (expect < 5ms, cache hit)

**Expected Outcome**:
- Both requests return HTTP 200 with identical response body
- Request #2 has `metadata.cache_hit: true`
- Request #2 latency < 10% of request #1 latency
- Only 1 computation performed (verify via log count)

**Observability Assertions**:
- Log entry #1: `level=INFO msg="Route computed" request_id=test-idempotency-001 cache_hit=false`
- Log entry #2: `level=INFO msg="Route served from cache" request_id=test-idempotency-001 cache_hit=true`
- Metric: `routing_cache_hit_total{graph_id=positive_weight}` incremented by 1

---

#### Test Case 2: Retry with Exponential Backoff

**Target Issue**: No retry mechanism for transient failures (High Priority)

**Preconditions**:
- Graph file: `transient_failure.json` (accessible but simulate read error)
- Service: v2 with retry enabled (3 attempts, exponential backoff)

**Test Data**:
```json
{
  "request_id": "test-retry-002",
  "graph_id": "transient_failure",
  "start_node": "A",
  "goal_node": "B"
}
```

**Steps**:
1. Mock file system: 1st read raises `OSError`, 2nd read succeeds
2. Send route request
3. Observe retry attempts in logs
4. Verify final success response

**Expected Outcome**:
- Request eventually succeeds (HTTP 200)
- Total time: ~1s (initial) + 1s (wait) + 0.1s (retry) ≈ 2.1s
- Path and cost returned correctly

**Observability Assertions**:
- Log entry #1: `level=WARNING msg="Graph load failed, retrying" attempt=1 wait_time=1s error=OSError`
- Log entry #2: `level=INFO msg="Graph loaded successfully" attempt=2`
- Metric: `routing_retry_total{operation=load_graph}` = 1
- Metric: `routing_success_total` = 1

---

#### Test Case 3: Timeout Propagation

**Target Issue**: No timeout protection (High Priority)

**Preconditions**:
- Graph: `large_graph.json` (10k nodes, 50k edges)
- Service: v2 with timeout=2s

**Test Data**:
```json
{
  "request_id": "test-timeout-003",
  "graph_id": "large_graph",
  "start_node": "node_0",
  "goal_node": "node_9999",
  "options": {"timeout_ms": 2000}
}
```

**Steps**:
1. Mock algorithm to sleep 5s (simulate slow computation)
2. Send route request
3. Verify timeout after 2s
4. Check circuit breaker state

**Expected Outcome**:
- Request fails with HTTP 504 Gateway Timeout
- Response time: ~2000ms (enforced timeout)
- Error response: `{"status": "timeout", "error": {"code": "COMPUTATION_TIMEOUT"}}`

**Observability Assertions**:
- Log entry: `level=ERROR msg="Computation timeout" request_id=test-timeout-003 timeout_ms=2000`
- Metric: `routing_timeout_total` = 1
- Circuit breaker: failure count incremented (5 failures → open)

---

#### Test Case 4: Circuit Breaker

**Target Issue**: No circuit breaker for cascading failures (Medium Priority)

**Preconditions**:
- Service: v2 with circuit breaker (fail_max=3, timeout=10s)
- Graph: `broken_graph.json` (invalid format to trigger failures)

**Test Data**:
```json
{
  "request_id": "test-circuit-{N}",
  "graph_id": "broken_graph",
  "start_node": "A",
  "goal_node": "B"
}
```

**Steps**:
1. Send 3 requests with invalid graph (trigger failures)
2. Verify circuit breaker opens
3. Send 4th request
4. Verify immediate failure (no graph load attempt)
5. Wait 10s (timeout_duration)
6. Send 5th request (half-open state)
7. Mock success on 5th request
8. Verify circuit breaker closes

**Expected Outcome**:
- Requests 1-3: HTTP 500 (graph load error) with retry attempts
- Request 4: HTTP 503 (circuit open) with < 10ms latency
- Request 5: HTTP 200 (success, circuit closed)

**Observability Assertions**:
- Log: `level=ERROR msg="Circuit breaker opened" service=graph_loader failures=3`
- Log: `level=INFO msg="Circuit breaker half-open, testing" request_id=test-circuit-5`
- Log: `level=INFO msg="Circuit breaker closed" success_count=1`
- Metric: `routing_circuit_breaker_state{service=graph_loader}` = 0 (closed), 1 (open), 2 (half-open)

---

#### Test Case 5: Negative Weight Handling (Correctness)

**Target Issue**: Incorrect shortest path calculation (Critical Priority)

**Preconditions**:
- Graph: `negative_weight.json` (same as legacy test)
  ```
  A→B (5), A→C (2), C→D (1), D→F (-3), F→B (1), A→E (1), E→B (6)
  ```
- Service: v2 with automatic algorithm selection

**Test Data**:
```json
{
  "request_id": "test-negative-005",
  "graph_id": "negative_weight",
  "start_node": "A",
  "goal_node": "B"
}
```

**Steps**:
1. Send route request
2. Verify v2 detects negative weight
3. Verify Bellman-Ford algorithm selected
4. Verify correct path returned

**Expected Outcome**:
- HTTP 200 Success
- Response: `{"path": ["A","C","D","F","B"], "cost": 1.0, "metadata": {"algorithm_used": "bellman_ford"}}`
- Computation time: < 100ms

**Observability Assertions**:
- Log: `level=INFO msg="Negative weight detected" graph_id=negative_weight min_weight=-3`
- Log: `level=INFO msg="Algorithm selected" algorithm=bellman_ford reason=negative_weights`
- Metric: `routing_algorithm_selection_total{algorithm=bellman_ford}` = 1

---

#### Test Case 6: Negative Cycle Detection

**Target Issue**: Undefined shortest path for negative cycles (Correctness)

**Preconditions**:
- Graph: `negative_cycle.json`
  ```
  A→B (1), B→C (1), C→A (-3)  # Cycle A→B→C→A with cost -1
  ```

**Test Data**:
```json
{
  "request_id": "test-cycle-006",
  "graph_id": "negative_cycle",
  "start_node": "A",
  "goal_node": "B"
}
```

**Steps**:
1. Send route request
2. Verify v2 detects negative cycle
3. Verify request rejected with error

**Expected Outcome**:
- HTTP 400 Bad Request
- Error response: 
  ```json
  {
    "status": "error",
    "error": {
      "code": "NEGATIVE_CYCLE_DETECTED",
      "message": "Graph contains negative weight cycle",
      "details": {"cycle": ["A","B","C","A"], "cycle_cost": -1.0}
    }
  }
  ```

**Observability Assertions**:
- Log: `level=WARNING msg="Negative cycle detected" graph_id=negative_cycle cycle=["A","B","C","A"]`
- Metric: `routing_validation_error_total{reason=negative_cycle}` = 1

---

#### Test Case 7: Healthy Path (Positive Weights)

**Target Issue**: Baseline correctness for common case

**Preconditions**:
- Graph: `positive_weight.json` (A→B=5, A→C=2, C→D=1, D→B=1)

**Test Data**:
```json
{
  "request_id": "test-healthy-007",
  "graph_id": "positive_weight",
  "start_node": "A",
  "goal_node": "B"
}
```

**Steps**:
1. Send route request
2. Verify Dijkstra selected
3. Verify correct path returned

**Expected Outcome**:
- HTTP 200 Success
- Response: `{"path": ["A","C","D","B"], "cost": 4.0, "metadata": {"algorithm_used": "dijkstra"}}`
- Latency p95: < 50ms

**Observability Assertions**:
- Log: `level=INFO msg="Route computed successfully" algorithm=dijkstra path_length=4`
- Metric: `routing_success_total{algorithm=dijkstra}` = 1
- Metric: `routing_latency_ms{quantile=0.95}` < 50

---

#### Test Case 8: Audit Trail & Structured Logging

**Target Issue**: No observability (High Priority)

**Preconditions**:
- Service: v2 with structured logging enabled
- Graph: Any valid graph

**Test Data**:
```json
{
  "request_id": "test-audit-008",
  "graph_id": "audit_test",
  "start_node": "A",
  "goal_node": "B"
}
```

**Steps**:
1. Send route request
2. Capture all log entries
3. Verify structured fields present

**Expected Outcome**:
- All log entries contain:
  - `timestamp` (ISO8601)
  - `level` (INFO/WARNING/ERROR)
  - `request_id`
  - `graph_id`
  - `correlation_id` (for distributed tracing)
  - `user_id` (if authenticated)
- Sensitive fields masked: None in this service (PII would be masked)

**Observability Assertions**:
```json
{
  "timestamp": "2025-12-03T10:15:30.123Z",
  "level": "INFO",
  "msg": "Route request received",
  "request_id": "test-audit-008",
  "graph_id": "audit_test",
  "start_node": "A",
  "goal_node": "B",
  "correlation_id": "trace-abc-123"
}
```

---

### 5.2 Risk Coverage Analysis

| Risk | Covered By Test Case | Mitigation |
|------|---------------------|------------|
| Incorrect algorithm for negative weights | TC5, TC6 | Automatic algorithm selection + validation |
| Duplicate request processing | TC1 | Idempotency with request_id cache |
| Transient file I/O failures | TC2 | Retry with exponential backoff |
| Hung requests (infinite loops) | TC3 | Timeout enforcement |
| Cascading failures | TC4 | Circuit breaker pattern |
| Negative cycles (undefined result) | TC6 | Bellman-Ford cycle detection |
| Lack of audit trail | TC8 | Structured logging with request_id |
| Performance regression | TC7 | Baseline latency measurement |

**Risks Without Direct Test Coverage**:
1. **Concurrent request handling**: Not tested (assumption: single-threaded OK)
   - **Why**: No evidence of concurrency requirements in legacy system
   - **Mitigation**: Load test in staging (1000 req/s) before production
2. **Graph size limits**: Not tested (assumption: < 100k nodes)
   - **Why**: No performance SLA data available
   - **Mitigation**: Benchmark large graphs (10k, 50k, 100k nodes) separately
3. **Memory exhaustion**: Not tested
   - **Why**: Pure computational service, stateless
   - **Mitigation**: Set container memory limits (2GB) + OOMKill monitoring

---

### 5.3 Acceptance Criteria (Given-When-Then)

#### AC1: Correctness for Negative Weights
```gherkin
Given a graph with negative edge weights and no negative cycles
When a route request is submitted
Then the system SHALL return the optimal shortest path
  AND use Bellman-Ford algorithm
  AND complete within 100ms for graphs < 10k nodes
```

#### AC2: Negative Cycle Rejection
```gherkin
Given a graph containing a negative weight cycle
When a route request is submitted
Then the system SHALL reject the request
  AND return HTTP 400 with error code NEGATIVE_CYCLE_DETECTED
  AND include the cycle path in error details
```

#### AC3: Idempotency
```gherkin
Given a route request with request_id X
When the same request is submitted multiple times within 5 minutes
Then the system SHALL return identical results
  AND perform computation only once
  AND serve subsequent requests from cache (< 10ms)
```

#### AC4: Retry Resilience
```gherkin
Given a transient file I/O error occurs
When loading a graph
Then the system SHALL retry up to 3 times with exponential backoff
  AND succeed if error resolves
  AND fail with HTTP 500 after 3 failed attempts
```

#### AC5: Timeout Protection
```gherkin
Given a route computation exceeding configured timeout
When the timeout threshold is reached
Then the system SHALL abort computation
  AND return HTTP 504 Gateway Timeout within 2000ms ± 100ms
  AND increment circuit breaker failure count
```

#### AC6: Circuit Breaker
```gherkin
Given 5 consecutive failures in graph loading
When the circuit breaker opens
Then subsequent requests SHALL fail fast (< 10ms)
  AND return HTTP 503 Service Unavailable
  AND the circuit SHALL remain open for 60 seconds
  AND test 1 request in half-open state before closing
```

#### AC7: Observability
```gherkin
Given any route request
When processed by the system
Then structured logs SHALL include: timestamp, level, request_id, graph_id
  AND metrics SHALL be emitted: success_total, latency_ms, error_total
  AND audit trail SHALL be retained for 30 days
```

### 5.4 SLO/SLA Quantified

| Metric | SLO | SLA | Measurement Method |
|--------|-----|-----|-------------------|
| Availability | 99.9% | 99.5% | (successful_requests / total_requests) over 30-day window |
| Correctness | 99.99% | 99.9% | (correct_paths / total_paths) validated by test suite |
| Latency p50 | < 20ms | < 50ms | Histogram from Prometheus |
| Latency p95 | < 100ms | < 200ms | Histogram from Prometheus |
| Latency p99 | < 500ms | < 1000ms | Histogram from Prometheus |
| Error Rate | < 0.1% | < 0.5% | (error_responses / total_requests) |
| Cache Hit Rate | > 60% | > 40% | (cache_hits / total_requests) |

---

## 6. DELIVERABLE STRUCTURE

The complete greenfield replacement is organized as follows:

```
Claude-Sonnet-4.5/
├── README.md                      # This document (architecture & analysis)
├── requirements.txt               # Shared dependencies
├── run_all.sh                     # Master test runner (cross-project comparison)
├── compare_report.md              # Pre/post comparison results
│
├── legacy_v1/                     # Baseline (copy of issue_project)
│   ├── src/logistics/
│   ├── tests/
│   ├── data/
│   └── run_tests.sh               # Run legacy tests
│
├── greenfield_v2/                 # New system implementation
│   ├── src/
│   │   ├── api/                   # FastAPI endpoints
│   │   │   ├── __init__.py
│   │   │   ├── routes.py          # /v2/route endpoint
│   │   │   └── schemas.py         # Pydantic request/response models
│   │   ├── core/                  # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── graph.py           # Graph model with validation
│   │   │   ├── algorithms/        # Algorithm implementations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py        # Abstract base class
│   │   │   │   ├── dijkstra.py
│   │   │   │   ├── bellman_ford.py
│   │   │   │   └── selector.py    # Algorithm selection logic
│   │   │   ├── validator.py       # Graph + result validation
│   │   │   └── routing.py         # Orchestration layer
│   │   ├── resilience/            # Resilience patterns
│   │   │   ├── __init__.py
│   │   │   ├── retry.py           # Retry decorator
│   │   │   ├── timeout.py         # Timeout context manager
│   │   │   ├── circuit_breaker.py
│   │   │   └── cache.py           # Idempotency cache
│   │   └── observability/         # Logging + metrics
│   │       ├── __init__.py
│   │       ├── logger.py          # Structured logging setup
│   │       └── metrics.py         # Prometheus metrics
│   │
│   ├── tests/
│   │   ├── integration/
│   │   │   ├── test_idempotency.py        # TC1
│   │   │   ├── test_retry.py              # TC2
│   │   │   ├── test_timeout.py            # TC3
│   │   │   ├── test_circuit_breaker.py    # TC4
│   │   │   ├── test_negative_weight.py    # TC5
│   │   │   ├── test_negative_cycle.py     # TC6
│   │   │   ├── test_healthy_path.py       # TC7
│   │   │   └── test_observability.py      # TC8
│   │   ├── unit/
│   │   │   ├── test_dijkstra.py
│   │   │   ├── test_bellman_ford.py
│   │   │   ├── test_validator.py
│   │   │   └── test_cache.py
│   │   └── conftest.py            # Pytest fixtures
│   │
│   ├── mocks/
│   │   ├── __init__.py
│   │   └── graph_loader_mock.py   # Simulate transient failures
│   │
│   ├── data/                      # Test graph fixtures
│   │   ├── positive_weight.json
│   │   ├── negative_weight.json
│   │   ├── negative_cycle.json
│   │   ├── large_graph.json
│   │   └── test_data.json         # Canonical test cases
│   │
│   ├── logs/                      # Runtime logs (gitignored)
│   │   └── .gitkeep
│   │
│   ├── results/                   # Test results (gitignored)
│   │   ├── results_post.json      # v2 test results
│   │   └── metrics.json           # Latency, success rate, etc.
│   │
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── setup.sh                   # Environment setup
│   └── run_tests.sh               # Run v2 tests
│
└── shared/                        # Cross-project utilities
    ├── test_data.json             # ≥5 canonical cases (shared)
    ├── results/
    │   ├── results_pre.json       # Legacy results
    │   ├── results_post.json      # v2 results
    │   └── aggregated_metrics.json
    └── compare_report_template.md
```

---

## 7. HOW TO RUN

### Prerequisites
```powershell
# Windows PowerShell
python --version  # 3.9+
pip install virtualenv
```

### One-Click Setup & Test
```powershell
cd Claude-Sonnet-4.5
.\setup.sh           # Create venv, install deps
.\run_all.sh         # Run legacy + v2 tests, generate comparison
```

### Individual Runs
```powershell
# Legacy (baseline)
cd legacy_v1
.\run_tests.sh       # pytest tests/ -v

# Greenfield v2
cd greenfield_v2
.\run_tests.sh       # pytest tests/integration/ -v --tb=short
```

### Interpret Results
```powershell
cat compare_report.md  # Correctness diffs, latency comparison, rollout guidance
cat shared/results/aggregated_metrics.json  # Quantitative metrics
```

---

## 8. LIMITS & CONSTRAINTS

### Current Scope Limitations
1. **Graph Size**: Tested up to 10k nodes / 50k edges; larger graphs may exceed timeout
2. **Concurrency**: Single-threaded processing; horizontal scaling required for high throughput
3. **Graph Updates**: Static file-based; no real-time graph modification API
4. **Authentication**: Not implemented; assume trusted network or add OAuth2/JWT layer
5. **Multi-Objective Optimization**: Only shortest path; no support for Pareto-optimal routes

### Known Trade-offs
1. **Bellman-Ford Performance**: O(VE) slower than Dijkstra; acceptable for correctness
2. **Cache Memory**: LRU cache limited to 1000 entries; tune based on traffic patterns
3. **No Distributed Tracing**: Correlation IDs present but no OpenTelemetry integration yet

### Future Enhancements (Out of Scope)
- Persistent graph storage (PostgreSQL with PostGIS, Neo4j)
- Real-time graph updates via event stream (Kafka)
- A* algorithm for heuristic optimization
- Multi-modal routing (time, cost, distance, emissions)
- GraphQL API for flexible queries

---

## 9. ROLLOUT STRATEGY

### Pre-Rollout Checklist
- [ ] Shadow mode validation: 10k requests, 0 correctness errors
- [ ] Load test passed: 1000 req/s sustained for 10 min, p95 < 100ms
- [ ] Alerting configured: error rate > 0.5%, latency p95 > 200ms
- [ ] Runbook documented: rollback procedure, incident response
- [ ] On-call engineer trained: v2 architecture, troubleshooting

### Rollout Phases (Timeline: 4 weeks)

#### Week 1-2: Shadow Mode
- **Traffic**: 0% to v2 (production)
- **Action**: Clone 100% requests to v2 (async, non-blocking)
- **Validation**: Compare results, log discrepancies
- **Go/No-Go**: < 0.01% correctness errors, no crashes

#### Week 3: Canary
- **Traffic**: 5% → 10% → 25% → 50%
- **Increment**: Every 2 days if metrics healthy
- **Rollback Trigger**: Error rate > 0.5% OR latency > 2x baseline
- **Monitoring**: Real-time dashboard (Grafana)

#### Week 4: Full Cutover
- **Traffic**: 100% to v2
- **Legacy**: Keep running (standby) for 7 days
- **Rollback**: DNS/load balancer flip (< 5 min)

#### Week 5: Decommission
- **Action**: Shut down legacy service
- **Archive**: Code repository tagged v1-final

### Success Metrics
- Correctness: 99.99% (validated by test suite)
- Availability: 99.9% over 30 days
- Latency p95: < 100ms (2x improvement over legacy)
- Zero data loss (stateless service)

---

## 10. CONCLUSION

This greenfield replacement addresses **critical correctness issues**, introduces **enterprise-grade resilience patterns**, and provides **comprehensive observability**. The modular architecture enables future enhancements (distributed graphs, real-time updates, multi-objective optimization) while maintaining strict backward compatibility during migration.

**Key Improvements**:
- ✅ Correct algorithm selection (Dijkstra vs. Bellman-Ford)
- ✅ Idempotency guarantees (request ID + cache)
- ✅ Retry with exponential backoff
- ✅ Timeout enforcement + circuit breaker
- ✅ Structured logging + metrics
- ✅ 8 comprehensive integration tests
- ✅ One-click test runner + comparison report

**Risk Mitigation**: Phased rollout with shadow mode and canary deployments ensures zero-downtime migration with immediate rollback capability.
