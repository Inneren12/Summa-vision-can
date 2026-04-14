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
Write-Host "Ctrl+C to stop`n" -ForegroundColor DarkGray

Set-Location "$root\backend"
& $python -m uvicorn src.main:app --reload --port 8000
