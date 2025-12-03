#!/usr/bin/env pwsh
# Run greenfield v2 tests

Write-Host "Running Greenfield v2 Tests..." -ForegroundColor Green

# Activate venv
.\.venv\Scripts\Activate.ps1

# Run tests with coverage
Write-Host "`nRunning integration tests..." -ForegroundColor Cyan
pytest tests/integration/ -v --tb=short --capture=no

# Run unit tests if they exist
if (Test-Path "tests/unit") {
    Write-Host "`nRunning unit tests..." -ForegroundColor Cyan
    pytest tests/unit/ -v --tb=short
}

Write-Host "`nTests complete!" -ForegroundColor Green
