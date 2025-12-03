$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot ".."))
$pre = Join-Path $root "issue_project"
$post = Join-Path $root "swe_vsc_mix4-nopreamble-rapidash60-s90"
$res = Join-Path $post "Shared/results"
New-Item -ItemType Directory -Force -Path $res | Out-Null

function Run-Pytest($dir, $outfile) {
  Push-Location $dir
  python -m venv .venv
  .\.venv\Scripts\activate.ps1
  pip install -r requirements.txt | Out-Null
  pytest -q 2>&1 | Tee-Object -FilePath $outfile
  deactivate
  Pop-Location
}

# Pre (legacy)
try { Run-Pytest $pre (Join-Path $res "results_pre.txt") } catch {}
# Post (v2)
Run-Pytest $post (Join-Path $res "results_post.txt")

$summary = @{ pre = @{ passed = 0; failed = 0 }; post = @{ passed = 0; failed = 0 } }
if (Test-Path (Join-Path $res "results_pre.txt")) {
  $txt = Get-Content (Join-Path $res "results_pre.txt") -Raw
  $summary.pre.passed = ([regex]::Matches($txt, "passed")).Count
  $summary.pre.failed = ([regex]::Matches($txt, "failed")).Count
}
if (Test-Path (Join-Path $res "results_post.txt")) {
  $txt = Get-Content (Join-Path $res "results_post.txt") -Raw
  $summary.post.passed = ([regex]::Matches($txt, "passed")).Count
  $summary.post.failed = ([regex]::Matches($txt, "failed")).Count
}
$summary | ConvertTo-Json | Set-Content (Join-Path $res "aggregated_metrics.json")
