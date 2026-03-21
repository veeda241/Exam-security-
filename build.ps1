# ExamGuard Pro - Unified Build Script for Windows (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "=== STARTING LOCAL WINDOWS BUILD ===" -ForegroundColor Cyan
Write-Host "Python Version: $(python --version)"
Write-Host "Node Version: $(node -v)"

# 1. Build Frontend
Write-Host "--- Installing Frontend & Building ---" -ForegroundColor Yellow
Set-Location react-frontend
npm install
npm run build
Set-Location ..

# 2. Aggregating Files
Write-Host "--- Preparing Distribution ---" -ForegroundColor Yellow
if (!(Test-Path server/dist)) {
    New-Item -ItemType Directory -Path server/dist
}
Copy-Item -Path "react-frontend/dist/*" -Destination "server/dist" -Recurse -Force

Write-Host "=== BUILD COMPLETE ===" -ForegroundColor Green
Get-ChildItem -Path server/dist
