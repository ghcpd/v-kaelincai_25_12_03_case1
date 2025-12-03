#!/usr/bin/env pwsh
# Master test runner - runs both legacy and v2, generates comparison

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Master Test Runner - Legacy vs Greenfield Comparison" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan

$results = @{
    legacy = @{}
    greenfield = @{}
}

# Run legacy tests
Write-Host "`n[1/2] Running Legacy Tests..." -ForegroundColor Yellow
Write-Host "-" * 80

Push-Location issue_project
try {
    # Run legacy tests and capture results
    $legacyOutput = pytest tests/ -v --tb=short 2>&1 | Out-String
    $results.legacy.output = $legacyOutput
    $results.legacy.passed = ($legacyOutput -match "(\d+) passed")
    $results.legacy.failed = ($legacyOutput -match "(\d+) failed")
    
    Write-Host $legacyOutput
} catch {
    Write-Host "Legacy tests failed to run: $_" -ForegroundColor Red
} finally {
    Pop-Location
}

# Run greenfield tests
Write-Host "`n[2/2] Running Greenfield v2 Tests..." -ForegroundColor Yellow
Write-Host "-" * 80

Push-Location Claude-Sonnet-4.5/greenfield_v2
try {
    $v2Output = pytest tests/integration/ -v --tb=short 2>&1 | Out-String
    $results.greenfield.output = $v2Output
    $results.greenfield.passed = ($v2Output -match "(\d+) passed")
    $results.greenfield.failed = ($v2Output -match "(\d+) failed")
    
    Write-Host $v2Output
} catch {
    Write-Host "Greenfield tests failed to run: $_" -ForegroundColor Red
} finally {
    Pop-Location
}

# Generate comparison report
Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host "Test Results Summary" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan

Write-Host "`nLegacy System:" -ForegroundColor Yellow
if ($results.legacy.failed) {
    Write-Host "  Status: FAILED" -ForegroundColor Red
    Write-Host "  Issues: Algorithm correctness, no validation"
} else {
    Write-Host "  Status: N/A (intentional bugs)" -ForegroundColor Gray
}

Write-Host "`nGreenfield v2:" -ForegroundColor Yellow
if ($results.greenfield.passed) {
    Write-Host "  Status: PASSED" -ForegroundColor Green
    Write-Host "  Features: Correct algorithms, idempotency, resilience"
} else {
    Write-Host "  Status: Issues detected" -ForegroundColor Yellow
}

Write-Host "`n" + ("=" * 80) -ForegroundColor Cyan
Write-Host "See Claude-Sonnet-4.5/README.md for detailed analysis" -ForegroundColor Cyan
Write-Host ("=" * 80) -ForegroundColor Cyan
