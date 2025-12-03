# oswe-mini-secondary — routing_service (greenfield replacement sample)

This mini-project demonstrates a greenfield replacement for a routing component with robust algorithms, lifecycle handling (idempotency, outbox), and tests that focus on crash points and operational risks.

Key components:
- src/routing_service: Graph, Algorithms (Dijkstra safe, Bellman-Ford), Router runtime (idempotency, outbox, lifecycle).
- tests/: Integration and unit tests covering negative-weight detection, algorithm selection, idempotency, timeouts, failure outbox.

Run tests (PowerShell):

```powershell
Set-Location -Path c:\chatWorkspace\oswe-mini-secondary
python -m pip install -r requirements.txt
pytest -q
```

Files to inspect:
- src/routing_service: core.py, graph.py, algorithms.py
- data: graph_negative_weight.json
