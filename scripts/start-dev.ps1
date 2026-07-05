# ExamGuard Pro V2 — local dev (Windows PowerShell, no Docker required for API)
# Usage: .\scripts\start-dev.ps1
# Optional: start Redis via Docker first — .\scripts\start-redis.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ServerDir = Join-Path $Root "server"
$VenvDir = Join-Path $ServerDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "=== ExamGuard Pro V2 — Dev Startup ===" -ForegroundColor Cyan

if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item (Join-Path $Root "deployment\env.example") (Join-Path $Root ".env")
    Write-Host "Created .env from deployment/env.example" -ForegroundColor Yellow
}

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv $VenvDir
}

Write-Host "Installing/updating Python dependencies..." -ForegroundColor Yellow
& $VenvPython -m pip install -q --upgrade pip
& $VenvPython -m pip install -q -r (Join-Path $ServerDir "requirements.txt")

Write-Host ""
Write-Host "Starting API on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  Health:  http://127.0.0.1:8000/health" -ForegroundColor Gray
Write-Host "  Docs:    http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host ""
Write-Host "In separate terminals (after Redis is running):" -ForegroundColor Yellow
Write-Host "  Worker:  .\scripts\start-worker.ps1" -ForegroundColor Gray
Write-Host "  Frontend: cd examguard-pro; npm run dev" -ForegroundColor Gray
Write-Host ""

Push-Location $ServerDir
& $VenvPython -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
