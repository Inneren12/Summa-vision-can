#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"

$root = Get-ProjectRoot
$python = Get-BackendPython
if (-not $python) { Write-Fail "Run bootstrap-backend.ps1 first"; exit 1 }

Assert-FileExists "$root\backend\.env" "Run bootstrap-backend.ps1"
Assert-PortFree 8000 "Backend API"

# Show config
$envFile = "$root\backend\.env"
$dbLine = (Get-Content $envFile | Select-String 'DATABASE_URL').ToString().Split('=',2)[1]
$mode = if ($dbLine -match "sqlite") { "Lite (SQLite)" } else { "Full (Postgres)" }
Write-Host "  Python: $python" -ForegroundColor DarkGray
Write-Host "  Mode: $mode" -ForegroundColor DarkGray

# Suggest alembic if needed
if ($dbLine -match "sqlite") {
    $dbPath = "$root\backend\summa_dev.db"
    if (-not (Test-Path $dbPath)) {
        Write-Host "  NOTE: DB not initialized" -ForegroundColor DarkYellow
        Write-Host "  Run: cd backend && $python -m alembic upgrade head" -ForegroundColor DarkYellow
    }
}

Write-Host "`nStarting backend -> http://localhost:8000" -ForegroundColor Cyan
Write-Host "Swagger -> http://localhost:8000/docs" -ForegroundColor White
Write-Host "Ctrl+C to stop`n" -ForegroundColor DarkGray

Set-Location "$root\backend"
& $python -m uvicorn src.main:app --reload --port 8000
