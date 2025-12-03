# Test validation summary (generated)

Generated: 2025-12-03

## issue_project (legacy)
- Test command: `pytest -q` run in `c:\chatWorkspace\issue_project`
- Result: 2 failed, 0 passed
- Failures:
  - test_dijkstra_rejects_negative_weights: expected ValueError (did not raise)
  - test_dijkstra_finds_optimal_path_despite_negative_edge: returned ['A','B'] instead of ['A','C','D','F','B']

Captured output (abridged):
```
FAILED tests/test_routing_negative_weight.py::test_dijkstra_rejects_negative_weights - Failed: DID NOT RAISE ValueError
FAILED tests/test_routing_negative_weight.py::test_dijkstra_finds_optimal_path_despite_negative_edge - AssertionError
2 failed, 106 warnings in 0.20s
```

## oswe-mini-secondary (greenfield replacement prototype)
- Test command: `pytest -q` run in `c:\chatWorkspace\oswe-mini-secondary`
- Result: 7 passed, 0 failed
- Tests run include algorithm validation (Dijkstra rejects negative weights), Bellman-Ford correctness, Router lifecycle tests (idempotency, outbox, timeout propagation, retries)

Captured output (abridged):
```
7 passed, 364 warnings in 0.29s
```

## Conclusion
- The new `oswe-mini-secondary` prototype's test suite passes completely.
- The legacy `issue_project` test suite fails 2 tests due to a Dijkstra implementation that both doesn't reject negative weights and incorrectly finalizes nodes.

## Next recommended actions
1. For `issue_project`: decide to either (a) implement negative-weight detection and raise a validation error in `dijkstra_shortest_path`, or (b) implement and switch to Bellman-Ford when negative weights are present. The greenfield `oswe-mini-secondary` provides an exemplar.
2. Add CI to run tests for both projects in the pipeline and include structured test artifacts for further investigation.
