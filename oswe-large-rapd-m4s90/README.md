# Routing Service v2 (swe_vsc_mix4-nopreamble-rapidash60-s90)

## Overview
* Greenfield replacement for legacy logistics routing (negative-weight aware).
* Provides idempotent, observable routing with algorithm selection (Dijkstra vs Bellman-Ford).
* Structured logging, lightweight metrics, transactional outbox stub, retry/backoff, and state machine.

## Layout
```
src/                # runtime code
mocks/api/v2/       # mock graph API (immediate/pending/delayed)
data/               # test_data.json, expected_postchange.json
tests/              # pytest integration tests
logs/               # sample log output
results/            # sample test results
Shared/             # cross-project scripts & reports (see ../Shared)
```

## Quickstart (PowerShell)
```powershell
python -m venv .venv; .\.venv\Scripts\activate; pip install -r requirements.txt; pytest -q tests
```

## Quickstart (bash)
```bash
./setup.sh
./run_tests.sh
```

## API (FastAPI)
* `POST /route` accepts `RouteRequest` (request_id, source, target, graph | graph_id).
* Returns `RouteResponse` with `status` ∈ {success,failure}, algorithm, path, cost, retries.

## Architecture (ASCII)
```
+-----------+     +----------------+     +----------------+     +------------------+
| Client    | --> | RouterService  | --> | Algorithm sel. | --> | Dijkstra/BF core |
+-----------+     | (idempotency,  |     +----------------+     +------------------+
                  | retry, metrics)|
                  +--------+-------+
                           |
                           v
                 +---------+---------+
                 | GraphLoader       |
                 | (file/API mocks)  |
                 +---------+---------+
                           |
                           v
                 +---------+--------+
                 | Outbox / Logs / |
                 | Metrics          |
                 +------------------+
```

## State Machine
* INIT → VALIDATED → FETCH_GRAPH → PLANNING → SUCCESS/FAILURE → COMPENSATED
* Crash points: graph load timeout, negative cycle detection, no path.

## Observability
* Structured JSON logs with `request_id`, `event`, `algorithm`, `path`, `cost`, `state`.
* Metrics counters: `success`, `failure`, `graph_load_attempts`, `idempotent_hits`.
* Outbox events recorded for reconciliation/audit.

## Idempotency & Retries
* `request_id` cache ensures repeat calls return identical response.
* `with_retry` wraps graph loading (exponential backoff).
* Timeouts supported via ThreadPool futures.

## Limits & Notes
* Metrics and outbox are in-memory; replace with persistent store for production.
* FastAPI app is optional; tests exercise service directly.
* Circuit breaker pattern can be added around `GraphLoader` if API becomes unstable.

## Rollout Strategy
1. Shadow traffic: run v2 in parallel, compare `results_pre.json` vs `results_post.json`.
2. Gradual cutover: enable write-path routing for a subset of tenants.
3. Monitor metrics/logs; rollback via feature flag if failure rate or latency regresses.

