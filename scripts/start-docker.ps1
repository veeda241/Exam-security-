# Full V2 stack via Docker Compose
# Usage: .\scripts\start-docker.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path (Join-Path $Root ".env"))) {
    Copy-Item (Join-Path $Root "deployment\env.example") (Join-Path $Root ".env")
    Write-Host "Created .env from deployment/env.example" -ForegroundColor Yellow
}

Push-Location $Root
Write-Host "Building and starting api + redis + worker + beat ..." -ForegroundColor Cyan
docker compose up --build
