#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "running tests for oswe-mini-secondary"
python -m pytest -q | tee results_pre.txt || true
