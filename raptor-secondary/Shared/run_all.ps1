Param()
$ErrorActionPreference = 'Stop'
$root = Split-Path (Split-Path (Split-Path $PSCommandPath -Parent) -Parent) -Parent
Push-Location $root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r issue_project\requirements.txt
pip install -r raptor-secondary\requirements.txt
# Pre: legacy
$prePath = Join-Path $root "raptor-secondary\Shared\results\results_pre.json"
Push-Location issue_project
pytest -q --rootdir . --disable-warnings -o pythonpath=src --json-report --json-report-file $prePath | Out-Null
Pop-Location
# Post: new system
$postPath = Join-Path $root "raptor-secondary\Shared\results\results_post.json"
Push-Location raptor-secondary
pytest -q --disable-warnings --json-report --json-report-file $postPath | Out-Null
Pop-Location
$pre = Get-Content raptor-secondary\Shared\results\results_pre.json -Raw | ConvertFrom-Json
$post = Get-Content $postPath -Raw | ConvertFrom-Json
$agg = [ordered]@{
  pre_failures = $pre.summary.failed
  post_failures = $post.summary.failed
  pre_summary = $pre.summary
  post_summary = $post.summary
}
$agg | ConvertTo-Json -Depth 5 | Set-Content raptor-secondary\Shared\results\aggregated_metrics.json
$agg | ConvertTo-Json -Depth 5
Pop-Location
