#!/usr/bin/env pwsh
# Facade: bootstrap everything
param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$FlutterOnly,
    [switch]$NoFlutter,
    [switch]$Lite,
    [switch]$Full
)

$backendArg = if ($Full) { "-Full" } else { "-Lite" }

if ($BackendOnly)  { & "$PSScriptRoot\bootstrap-backend.ps1" $backendArg; exit $LASTEXITCODE }
if ($FrontendOnly) { & "$PSScriptRoot\bootstrap-frontend.ps1"; exit $LASTEXITCODE }
if ($FlutterOnly)  { & "$PSScriptRoot\bootstrap-flutter.ps1"; exit $LASTEXITCODE }

& "$PSScriptRoot\bootstrap-backend.ps1" $backendArg
if ($LASTEXITCODE -ne 0) { exit 1 }

& "$PSScriptRoot\bootstrap-frontend.ps1"
if ($LASTEXITCODE -ne 0) { exit 1 }

if (-not $NoFlutter) {
    & "$PSScriptRoot\bootstrap-flutter.ps1"
    # Flutter failure is non-fatal
}
