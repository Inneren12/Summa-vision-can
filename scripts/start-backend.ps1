#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"

$root = Get-ProjectRoot
$python = Get-BackendPython

if (-not $python) {
    Write-Fail "Backend not bootstrapped. Run: .\scripts\bootstrap-backend.ps1"
    exit 1
}

Assert-FileExists "$root\backend\.env" "Run .\scripts\bootstrap-backend.ps1"
Assert-PortFree 8000 "Backend API"

Write-Host "Starting backend -> http://localhost:8000" -ForegroundColor Cyan
Write-Host "Swagger -> http://localhost:8000/docs" -ForegroundColor White

Write-Host "  Python: $($python)" -ForegroundColor DarkGray
Write-Host "  .env: $(Get-Content "$root\backend\.env" | Select-String 'DATABASE_URL' | ForEach-Object { $_.ToString().Split('=',2)[1].Substring(0,20) })..." -ForegroundColor DarkGray

# Suggest migration if DB file doesn't exist (SQLite) or tables missing
$dbUrl = Get-Content "$root\backend\.env" | Select-String 'DATABASE_URL' | ForEach-Object { $_.ToString().Split('=',2)[1] }
if ($dbUrl -match "sqlite" -and -not (Test-Path "$root\backend\summa_dev.db")) {
    Write-Host "  NOTE: DB not initialized. Run: cd backend && $python -m alembic upgrade head" -ForegroundColor DarkYellow
}

Write-Host "Ctrl+C to stop`n" -ForegroundColor DarkGray

Set-Location "$root\backend"
& $python -m uvicorn src.main:app --reload --port 8000
