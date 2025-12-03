# Shared Runner

## One-click fixture
```bash
./run_all.sh
```
* Runs legacy `issue_project` tests (expected failures for negative weights).
* Runs v2 tests in `swe_vsc_mix4-nopreamble-rapidash60-s90`.
* Produces artifacts in `Shared/results/`:
  * `results_pre.txt`, `results_post.txt` (raw pytest output)
  * `aggregated_metrics.json` (counts)
  * `compare_report.md` (summary)

## PowerShell
```powershell
bash Shared/run_all.sh
```

## Interpreting Results
* `results_pre.txt`: legacy failing cases
* `results_post.txt`: v2 passes
* `compare_report.md`: correctness diff, latency placeholders, rollout guidance

