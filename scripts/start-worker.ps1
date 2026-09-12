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

# Load simple KEY=VALUE entries from server/.env because Celery reads Redis
# settings directly from the process environment.
$EnvFile = Join-Path $ServerDir ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line -match "^([^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"')
            if (-not (Get-Item "Env:$name" -ErrorAction SilentlyContinue)) {
                Set-Item "Env:$name" $value
            }
        }
    }
}

# Do not overwrite managed Redis credentials from server/.env. These defaults
# are only for an unauthenticated local Redis container.
if (-not $env:REDIS_URL) {
    $env:REDIS_URL = "redis://localhost:6379/0"
}
if (-not $env:CELERY_BROKER_URL) {
    $env:CELERY_BROKER_URL = $env:REDIS_URL
}
if (-not $env:CELERY_RESULT_BACKEND) {
    $env:CELERY_RESULT_BACKEND = $env:REDIS_URL
}

Push-Location $ServerDir
& $VenvPython -m celery -A workers.celery_app worker --loglevel=info -Q face,object,gaze,ocr,nlp,report,default -c 2
