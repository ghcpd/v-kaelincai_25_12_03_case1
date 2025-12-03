# Compare Report - routing_service replacement

Summary: Created a safe Dijkstra and Bellman-Ford replacement, plus a Router runtime with idempotency and outbox. The new code addresses negative-weight support, idempotency, and lifecycle handling.

Key improvements:
- Rejects/auto-selects algorithms when negative weights present
- Idempotency: reuse final results when retries happen
- Outbox pattern: record downstream events for eventual delivery
 
Rollout guidance:
1. Deploy behind feature flag; shadow production traffic to the new service.
2. Run replay tests against historical inputs and compare p50/p95, error rates.
3. Do dual-write/backfill where necessary, validate reconciliation.
