#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"
$python = Get-BackendPython
if (-not $python) { Write-Fail "Run bootstrap-backend.ps1 first"; exit 1 }
Set-Location "$(Get-ProjectRoot)\backend"
& $python -m pytest -q --tb=short @args
