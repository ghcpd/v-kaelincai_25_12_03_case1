# Compare Report

## Rollout Guidance
- Run `Shared/run_all.sh` or `Shared/run_all.ps1` to execute legacy and new suites.
- Monitor `Shared/results/aggregated_metrics.json` for failure deltas.

## Metrics (template)
| Metric | Legacy (pre) | New (post) |
|--------|--------------|------------|
| Failures | TBA | TBA |
| p50 latency | TBA | TBA |
| p95 latency | TBA | TBA |
| Errors/retries | TBA | TBA |

## Notes
- Populate latency metrics from test harness instrumentation.
- Review structured logs in `raptor-secondary/logs`.
