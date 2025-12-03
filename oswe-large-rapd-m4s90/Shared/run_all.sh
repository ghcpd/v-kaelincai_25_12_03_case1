#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PRE="$ROOT/issue_project"
POST="$ROOT/swe_vsc_mix4-nopreamble-rapidash60-s90"
RES="$POST/Shared/results"
mkdir -p "$RES"

run_pytest() {
  local dir="$1"; local outfile="$2"; shift 2
  pushd "$dir" >/dev/null
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt >/dev/null
  pytest -q "$@" 2>&1 | tee "$outfile"
  local code=${PIPESTATUS[0]}
  deactivate
  popd >/dev/null
  return $code
}

# Pre (legacy)
run_pytest "$PRE" "$RES/results_pre.txt" || true
# Post (v2)
run_pytest "$POST" "$RES/results_post.txt" tests

python - <<'PYCODE'
import json, re, sys
root = "${ROOT}"
res_dir = f"{root}/swe_vsc_mix4-nopreamble-rapidash60-s90/Shared/results"
import os
pre_txt = open(f"{res_dir}/results_pre.txt").read() if os.path.exists(f"{res_dir}/results_pre.txt") else ""
post_txt = open(f"{res_dir}/results_post.txt").read() if os.path.exists(f"{res_dir}/results_post.txt") else ""

def summarize(txt):
    passed = len(re.findall(r"passed", txt))
    failed = len(re.findall(r"failed", txt))
    return {"passed": passed, "failed": failed}

summary = {
    "pre": summarize(pre_txt),
    "post": summarize(post_txt),
}
open(f"{res_dir}/aggregated_metrics.json", "w").write(json.dumps(summary, indent=2))
PYCODE
