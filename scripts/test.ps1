#!/usr/bin/env pwsh
# Facade: run all tests
param(
    [switch]$BackendOnly, [switch]$FrontendOnly, [switch]$FlutterOnly, [switch]$NoFlutter
)

if ($BackendOnly)  { & "$PSScriptRoot\test-backend.ps1" @args; exit $LASTEXITCODE }
if ($FrontendOnly) { & "$PSScriptRoot\test-frontend.ps1" @args; exit $LASTEXITCODE }
if ($FlutterOnly)  { & "$PSScriptRoot\test-flutter.ps1" @args; exit $LASTEXITCODE }

$failed = 0

Write-Host "=== ALL TESTS ===" -ForegroundColor Cyan

Write-Host "`n--- Backend ---" -ForegroundColor Yellow
& "$PSScriptRoot\test-backend.ps1" @args
if ($LASTEXITCODE -ne 0) { $failed++ }

Write-Host "`n--- Frontend ---" -ForegroundColor Yellow
& "$PSScriptRoot\test-frontend.ps1" @args
if ($LASTEXITCODE -ne 0) { $failed++ }

if (-not $NoFlutter) {
    Write-Host "`n--- Flutter ---" -ForegroundColor Yellow
    & "$PSScriptRoot\test-flutter.ps1" @args
    if ($LASTEXITCODE -ne 0) { $failed++ }
}

Write-Host "`n=== $failed suite(s) failed ===" -ForegroundColor $(if ($failed -eq 0) {"Cyan"} else {"Red"})
exit $failed
