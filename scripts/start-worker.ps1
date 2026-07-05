# Celery worker for local dev (requires Redis on localhost:6379)
# Usage: .\scripts\start-worker.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ServerDir = Join-Path $Root "server"
$VenvPython = Join-Path $ServerDir ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Run .\scripts\start-dev.ps1 first to create the venv." -ForegroundColor Red
    exit 1
}

$env:REDIS_URL = "redis://localhost:6379/0"
$env:CELERY_BROKER_URL = "redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

Push-Location $ServerDir
& $VenvPython -m celery -A workers.celery_app worker --loglevel=info -Q face,object,gaze,ocr,nlp,report,default -c 2
