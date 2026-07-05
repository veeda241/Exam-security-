# ExamGuard Pro — Supabase database setup (Windows)
# Usage: .\scripts\setup-supabase.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$ServerDir = Join-Path $Root "server"
$VenvPython = Join-Path $ServerDir ".venv\Scripts\python.exe"

Write-Host "=== ExamGuard Pro — Supabase Schema Setup ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Option A — SQL Editor (recommended if pooler connection fails):" -ForegroundColor Yellow
Write-Host "  1. Open https://supabase.com/dashboard → your project → SQL Editor"
Write-Host "  2. Paste contents of: server\migrations\supabase_schema.sql"
Write-Host "  3. Click Run"
Write-Host "  4. Then run: cd server; python create_admin.py"
Write-Host ""
Write-Host "Option B — Automated (requires PG_HOST/PG_PASSWORD in server\.env):" -ForegroundColor Yellow

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating venv..." -ForegroundColor Gray
    python -m venv (Join-Path $ServerDir ".venv")
}

& $VenvPython -m pip install -q psycopg2-binary
Push-Location $ServerDir
try {
    & $VenvPython setup_database.py --seed-admin
} catch {
    Write-Host ""
    Write-Host "Automated setup failed. Use Option A (SQL Editor) above." -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Done. Set SUPABASE_KEY to service_role key in server\.env for full API access." -ForegroundColor Green
