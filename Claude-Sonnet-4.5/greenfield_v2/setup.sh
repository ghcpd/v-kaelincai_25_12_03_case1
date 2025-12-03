#!/usr/bin/env pwsh
# Setup script for greenfield v2

Write-Host "Setting up Greenfield v2 environment..." -ForegroundColor Green

# Create virtual environment
if (!(Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
.\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "Run tests with: .\run_tests.sh" -ForegroundColor Yellow
