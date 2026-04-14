#!/usr/bin/env pwsh
# Facade: start services
param(
    [switch]$BackendOnly,
    [switch]$PublicOnly,
    [switch]$FlutterOnly,
    [switch]$NoFlutter
)

. "$PSScriptRoot\lib\common.ps1"

if ($BackendOnly)  { & "$PSScriptRoot\start-backend.ps1"; exit $LASTEXITCODE }
if ($PublicOnly)   { & "$PSScriptRoot\start-frontend.ps1"; exit $LASTEXITCODE }
if ($FlutterOnly)  { & "$PSScriptRoot\start-flutter.ps1"; exit $LASTEXITCODE }

# Default: start backend + frontend in parallel
Write-Host "Starting backend + frontend..." -ForegroundColor Cyan

# Start backend
$be = Start-Job -ScriptBlock { & "$using:PSScriptRoot\start-backend.ps1" }

# Wait for backend readiness (max 30 seconds)
Write-Host "  Waiting for backend..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep 1
    try {
        $resp = Invoke-RestMethod "http://localhost:8000/api/health" -TimeoutSec 2 -ErrorAction Stop
        if ($resp.status -eq "ok") { $ready = $true; break }
    } catch {}
}
if (-not $ready) {
    Write-Fail "Backend failed to start within 30s"
    Receive-Job $be
    Stop-Job $be; Remove-Job $be
    exit 1
}
Write-OK "Backend ready"

# Now start frontend
$fe = Start-Job -ScriptBlock { & "$using:PSScriptRoot\start-frontend.ps1" }

$fl = $null
if (-not $NoFlutter) {
    Start-Sleep 2
    $fl = Start-Job -ScriptBlock { & "$using:PSScriptRoot\start-flutter.ps1" }
}

Write-Host "`n=== ALL SERVICES STARTING ===" -ForegroundColor Cyan
Write-Host "  Backend:    http://localhost:8000/docs"
Write-Host "  Frontend:   http://localhost:3000"
if (-not $NoFlutter) { Write-Host "  Flutter:    http://localhost:8082" }
Write-Host "`nCtrl+C to stop all`n" -ForegroundColor DarkGray

$jobs = @($be, $fe)
if (-not $NoFlutter -and $fl) { $jobs += $fl }

try {
    while ($true) {
        foreach ($j in $jobs) {
            if ($j.State -eq "Failed" -or $j.State -eq "Completed") {
                Write-Fail "Service died: $($j.Name)"
                Receive-Job $j
                throw "Service crashed"
            }
        }
        Receive-Job $jobs -ErrorAction SilentlyContinue
        Start-Sleep 2
    }
} finally {
    Stop-Job $jobs -ErrorAction SilentlyContinue
    Remove-Job $jobs -ErrorAction SilentlyContinue
}
