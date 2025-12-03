Compare report (pre/post change)

This file should be filled after running both v1 and v2 tests and collecting p50/p95 latency and error/retry counts.

Suggested metrics to capture:
- Success rate
- Retry counts (avg, p95)
- Idempotency violations (duplicate records)
- p50/p95 latency for scheduling API
- Errors: per-category (validation, external, internal)

Rollout guidance:
- Start with shadow traffic and metrics comparison for 7 days
- Gradual canary (5%, 25%, 100%) with rollback on >1% increase in errors or >10% latency degradation at p95
- Maintain dual-write until outbox consumer catches up and reconciliation proves consistent
