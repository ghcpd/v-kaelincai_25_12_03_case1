# Compare Report: Legacy vs v2

## Correctness
| Case                      | Legacy (pre)         | v2 (post)               | Notes |
|---------------------------|----------------------|-------------------------|-------|
| negative_edge_supported   | WRONG path A→B (5)   | ✅ A→C→D→F→B (1)         | Bellman-Ford |
| negative_cycle            | ❌ likely infinite/err| ✅ rejects negative cycle| Validation |
| no_path                   | ❌ may raise late     | ✅ clear error          | UX |
| idempotent_repeat         | ❌ not supported      | ✅ cached               | Idempotency |
| timeout_retry             | ❌ none               | ✅ retries + backoff   | Resiliency |

## Latency (illustrative)
| Metric     | Legacy | v2 |
|------------|--------|----|
| p50 (ms)   | 5      | 7  |
| p95 (ms)   | 8      | 12 |
| Retry rate | n/a    | 5% |

## Errors/Retry
* Legacy: fails silently or incorrect answers on negative weights.
* v2: structured errors, retry cap (3), idempotency cache.

## Rollout Guidance
1. Shadow mode: mirror traffic to v2, compare `results_pre.txt` vs `results_post.txt`.
2. Gate on metrics: correctness 100% on canary, p95 < 50ms.
3. Progressive rollout: 5% → 25% → 50% → 100%; feature-flag rollback.

