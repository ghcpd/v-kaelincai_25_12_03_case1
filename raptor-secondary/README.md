# Raptor Secondary (Preview)

A greenfield replacement reference for a logistics/appointment routing service with robust idempotency, retries, timeouts, circuit breakers, and compensation (Saga/outbox).

## Layout
- `src/raptor_secondary`: runtime (domain, services, adapters, infra)
- `mocks/`: `/api/v2` mock behavior (immediate/pending/delayed)
- `data/`: test data and expected outputs
- `tests/`: integration tests
- `logs/`: structured logs
- `results/`: JSON test results
- `Shared/`: cross-project orchestration & reports

## Quickstart (PowerShell)
```powershell
cd raptor-secondary
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
pytest -q
```

## Goals
- Clear lifecycle: init → in-progress → success/failure; crash points marked.
- Idempotency keys, retry with backoff, circuit breaker, transactional outbox.
- Integration tests & one-click fixtures.
- Structured logging with request/appointment IDs, masked sensitive fields.
