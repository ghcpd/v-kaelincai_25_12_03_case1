Current-State Scan & Root Cause Analysis

Summary of evidence from `issue_project`:
- Tests in `tests/test_routing_negative_weight.py` define contradictory expectations: one expects rejection of negative weights; another asserts algorithm returns optimal path despite negative weight.
- `routing.py` implements Dijkstra but marks nodes visited on discovery and does not reject negative weights; `graph.py` loads JSON graph files.
- `KNOWN_ISSUE.md` documents the negative-weight bug and suggests fixes.

Issues by category

| Category       | Symptom                                                 | Likely Root Cause                                                  | Evidence / Needed Evidence |
|---------------:|---------------------------------------------------------|--------------------------------------------------------------------|----------------------------|
| Functionality  | Wrong shortest path on graphs with negative edges       | Dijkstra run on negative-weight graph + premature node finalization | `routing.py` visited/mark logic; `KNOWN_ISSUE.md` |
| Performance    | Unknown for large graphs; algorithm naive               | In-memory adjacency dict and naive Dijkstra, no optimization or heuristics (A*, contraction) | Need size/volume expectations and benchmarks |
| Reliability    | No error handling or retries; missing logging           | Library lacks structured logs and defensive checks                 | Observe usage in consumer apps; add logs & errors |
| Security      | No secrets or network surface; limited attack surface   | Not applicable for current library, but could be if turned into a service | Check deployment context |
| Maintainability| Minimal tests; contradictory tests indicate unclear spec| Ambiguous requirements; missing API contract and lack of documentation | Tests and README exist but mismatch |
| Cost          | Low (library) but unknown if turned into infra; potential cost if run at scale | Need traffic and deployment model | Monitoring data required |

High-priority issues and validation

1) Negative weight handling (High)
- Hypothesis: Code should either reject negative weights or use Bellman-Ford; current code miscomputes path because nodes are marked visited too early.
- Validation: Run tests using provided `graph_negative_weight.json` and check for cost path difference. Add negative-weight detection and verify tests pass/fail accordingly.
- Fix path: Implement Bellman-Ford OR validate and raise ValueError before Dijkstra. Also fix visited marking to finalize nodes on heap pop.

2) Ambiguous spec & tests (High)
- Hypothesis: Tests reflect a confusion in expectations (one test expects rejection, one expects correct shortest path). Stakeholder input required to pick desired behavior.
- Validation: Ask product owner or check historical commits/PRs for intended behavior.
- Fix path: Clarify spec, update tests accordingly.

3) Missing logging & observability (Medium)
- Hypothesis: Consumers cannot debug issues due to lack of structured logs and correlation IDs.
- Validation: Search for logging usage in consumer repos; add structured logger and request/trace ID support.
- Fix path: Add logging wrapper, include `request_id` parameter when used in services.

Next step: Design greenfield replacement architecture (v2) including service decomposition, state machine, idempotency and testing strategy.