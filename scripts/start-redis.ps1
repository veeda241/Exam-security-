# Start Redis only via Docker (for local dev without full compose stack)
# Usage: .\scripts\start-redis.ps1

$ErrorActionPreference = "Stop"
Write-Host "Starting Redis on localhost:6379 ..." -ForegroundColor Cyan
docker run --rm -p 6379:6379 --name examguard-redis redis:7-alpine
