# Run ExamGuard Pro locally (Windows PowerShell)
# Usage: .\scripts\start-dev.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== ExamGuard Pro - Dev Startup ===" -ForegroundColor Cyan

# Build frontend if dist is missing
$DistDir = Join-Path $Root "examguard-pro\dist\index.html"
if (-not (Test-Path $DistDir)) {
    Write-Host "Building dashboard..." -ForegroundColor Yellow
    Push-Location (Join-Path $Root "examguard-pro")
    npm install
    npm run build
    Pop-Location
}

Write-Host ""
Write-Host "Starting backend on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "  Dashboard:  http://127.0.0.1:8000/" -ForegroundColor Gray
Write-Host "  API docs:   http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host "  Extension:  Load unpacked -> extension/ folder in Chrome" -ForegroundColor Gray
Write-Host ""
Write-Host "Optional: run dashboard with hot reload in another terminal:" -ForegroundColor Yellow
Write-Host "  cd examguard-pro && npm run dev" -ForegroundColor Gray
Write-Host ""

Push-Location (Join-Path $Root "server")
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
