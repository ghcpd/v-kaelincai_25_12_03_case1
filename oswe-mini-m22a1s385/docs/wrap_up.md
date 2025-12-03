Wrap-up: Work completed

Completed artifacts:
- docs/: collection_checklist.md, background.md, current_state_rca.md, architecture.md, wrap_up.md
- src/: scheduling implementation with Bellman-Ford and corrected Dijkstra, service layer with idempotency and outbox
- mocks/: external_calendar mock to simulate failures and delays
- tests/: integration tests for idempotency, retry/backoff, negative weight handling, dead-letter behavior
- scripts: setup.sh, run_tests.sh, run_all.sh, requirements.txt
- results/logs placeholders

How to run tests (Windows PowerShell):
python -m venv .venv; .\.venv\Scripts\Activate; python -m pip install -r requirements.txt; .\.venv\Scripts\pytest -q

Next recommended actions:
- Add CI pipeline to run tests and collect metrics
- Add integration with real calendar service and circuit-breaker library
- Add persistent DB and transactional outbox implementation
- Add monitoring dashboards and SLOs for p95 latency and availability
