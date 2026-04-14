#!/usr/bin/env pwsh
# Facade: bootstrap everything
param(
    [switch]$BackendOnly, [switch]$FrontendOnly, [switch]$FlutterOnly,
    [switch]$NoFlutter, [switch]$Lite, [switch]$Full
)

if ($BackendOnly)  { & "$PSScriptRoot\bootstrap-backend.ps1" $(if ($Full) {"-Full"} else {"-Lite"}); exit $LASTEXITCODE }
if ($FrontendOnly) { & "$PSScriptRoot\bootstrap-frontend.ps1"; exit $LASTEXITCODE }
if ($FlutterOnly)  { & "$PSScriptRoot\bootstrap-flutter.ps1"; exit $LASTEXITCODE }

$results = @()

& "$PSScriptRoot\bootstrap-backend.ps1" $(if ($Full) {"-Full"} else {"-Lite"})
$results += @{name="Backend"; ok=$($LASTEXITCODE -eq 0)}

& "$PSScriptRoot\bootstrap-frontend.ps1"
$results += @{name="Frontend"; ok=$($LASTEXITCODE -eq 0)}

if (-not $NoFlutter) {
    & "$PSScriptRoot\bootstrap-flutter.ps1"
    $results += @{name="Flutter"; ok=$($LASTEXITCODE -eq 0)}
}

Write-Host "`n=== BOOTSTRAP SUMMARY ===" -ForegroundColor Cyan
foreach ($r in $results) {
    $icon = if ($r.ok) { "OK" } else { "FAIL" }
    $color = if ($r.ok) { "Green" } else { "Red" }
    Write-Host "  $icon  $($r.name)" -ForegroundColor $color
}
