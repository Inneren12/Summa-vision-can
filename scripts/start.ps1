#!/usr/bin/env pwsh
# Facade: start services
param(
    [switch]$BackendOnly,
    [switch]$PublicOnly,
    [switch]$FlutterOnly,
    [switch]$NoFlutter
)

if ($BackendOnly)  { & "$PSScriptRoot\start-backend.ps1"; exit $LASTEXITCODE }
if ($PublicOnly)   { & "$PSScriptRoot\start-frontend.ps1"; exit $LASTEXITCODE }
if ($FlutterOnly)  { & "$PSScriptRoot\start-flutter.ps1"; exit $LASTEXITCODE }

# Default: start backend + frontend in parallel
Write-Host "Starting backend + frontend..." -ForegroundColor Cyan
$be = Start-Job -ScriptBlock { & "$using:PSScriptRoot\start-backend.ps1" }
Start-Sleep 3
$fe = Start-Job -ScriptBlock { & "$using:PSScriptRoot\start-frontend.ps1" }

if (-not $NoFlutter) {
    Start-Sleep 2
    $fl = Start-Job -ScriptBlock { & "$using:PSScriptRoot\start-flutter.ps1" }
}

Write-Host "`n=== ALL SERVICES STARTING ===" -ForegroundColor Cyan
Write-Host "  Backend:    http://localhost:8000/docs"
Write-Host "  Frontend:   http://localhost:3000"
if (-not $NoFlutter) { Write-Host "  Flutter:    http://localhost:8082" }
Write-Host "`nCtrl+C to stop all`n" -ForegroundColor DarkGray

try {
    while ($true) {
        $jobs = @($be, $fe)
        if (-not $NoFlutter -and $fl) { $jobs += $fl }
        Receive-Job $jobs -ErrorAction SilentlyContinue
        Start-Sleep 2
    }
} finally {
    $jobs = @($be, $fe)
    if (-not $NoFlutter -and $fl) { $jobs += $fl }
    Stop-Job $jobs -ErrorAction SilentlyContinue
    Remove-Job $jobs -ErrorAction SilentlyContinue
}
