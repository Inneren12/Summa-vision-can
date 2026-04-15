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

Write-Host "=== STARTING SUMMA VISION ===" -ForegroundColor Cyan
$psExe = (Get-Command powershell.exe -ErrorAction Stop).Source

# -- Backend in new window --
Write-Host "`n  Launching backend..." -ForegroundColor Yellow
Start-Process $psExe -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start-backend.ps1" `
    -WorkingDirectory (Get-ProjectRoot)

# Wait for backend readiness
Write-Host "  Waiting for backend health..." -ForegroundColor Yellow
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep 1
    try {
        $resp = Invoke-WebRequest "http://localhost:8000/api/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
}
if (-not $ready) {
    Write-Fail "Backend didn't start within 30s - check the backend window"
    exit 1
}
Write-OK "Backend alive on :8000"

# -- Frontend in new window --
Write-Host "`n  Launching frontend..." -ForegroundColor Yellow
Start-Process $psExe -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start-frontend.ps1" `
    -WorkingDirectory (Get-ProjectRoot)

# Wait for frontend
Write-Host "  Waiting for frontend..." -ForegroundColor Yellow
$feReady = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep 1
    try {
        $resp = Invoke-WebRequest "http://localhost:3000" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($resp.StatusCode -eq 200) { $feReady = $true; break }
    } catch {}
}
if ($feReady) { Write-OK "Frontend alive on :3000" }
else { Write-Host "  !!  Frontend still compiling - check the frontend window" -ForegroundColor DarkYellow }

# -- Flutter in new window (optional) --
if (-not $NoFlutter) {
    $fl = Get-FlutterCmd
    if ($fl) {
        Write-Host "`n  Launching Flutter..." -ForegroundColor Yellow
        Start-Process $psExe -ArgumentList "-NoExit", "-File", "$PSScriptRoot\start-flutter.ps1" `
            -WorkingDirectory (Get-ProjectRoot)
        Write-Host "  -> Flutter launched in new window (:8082) - check window for status" -ForegroundColor DarkYellow
    } else {
        Write-Host "  !! Flutter not found - skipping" -ForegroundColor DarkYellow
    }
}

# -- Summary --
Write-Host "`n=== ALL SERVICES LAUNCHED ===" -ForegroundColor Cyan
Write-Host "  Backend:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend:   http://localhost:3000" -ForegroundColor White
Write-Host "  Calculator: http://localhost:3000/insights/metr/calculator" -ForegroundColor White
if (-not $NoFlutter) {
    Write-Host "  Flutter:    http://localhost:8082 (open URL manually)" -ForegroundColor White
}
Write-Host "`n  Each service runs in its own terminal window." -ForegroundColor DarkGray
Write-Host "  Close windows individually with Ctrl+C." -ForegroundColor DarkGray