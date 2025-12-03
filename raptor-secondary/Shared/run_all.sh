#!/usr/bin/env bash
set -euo pipefail
root_dir=$(cd "$(dirname "$0")/../.." && pwd)
cd "$root_dir"
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r issue_project/requirements.txt
pip install -r raptor-secondary/requirements.txt
# Pre: legacy
cd issue_project
pytest -q --rootdir . --disable-warnings -o pythonpath=src --json-report --json-report-file=../raptor-secondary/Shared/results/results_pre.json || true
cd ..
# Post: new system
cd raptor-secondary
pytest -q --disable-warnings --json-report --json-report-file=../Shared/results/results_post.json || true
cd ..
python - <<'PY'
import json, pathlib
root = pathlib.Path('raptor-secondary/Shared/results')
pre = json.loads(root.joinpath('results_pre.json').read_text()) if root.joinpath('results_pre.json').exists() else {}
post = json.loads(root.joinpath('results_post.json').read_text()) if root.joinpath('results_post.json').exists() else {}
agg = {
    'pre_failures': pre.get('summary', {}).get('failed', None),
    'post_failures': post.get('summary', {}).get('failed', None),
    'pre_summary': pre.get('summary'),
    'post_summary': post.get('summary'),
}
root.joinpath('aggregated_metrics.json').write_text(json.dumps(agg, indent=2))
print(json.dumps(agg, indent=2))
PY
