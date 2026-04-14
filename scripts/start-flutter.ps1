#!/usr/bin/env pwsh
param([int]$Port = 8082)

. "$PSScriptRoot\lib\common.ps1"

$root = Get-ProjectRoot
$fl = Get-FlutterCmd
if (-not $fl) {
    Write-Fail "Flutter not found. Run: .\scripts\bootstrap-flutter.ps1"
    exit 1
}

Assert-PortFree $Port "Flutter web-server"

Write-Host "Starting Flutter web-server on :$Port..." -ForegroundColor Cyan
Write-Host "  SDK: $fl" -ForegroundColor DarkGray
Write-Host "  Open URL manually in browser" -ForegroundColor DarkYellow
Write-Host "  Ctrl+C to stop`n" -ForegroundColor DarkGray

Set-Location "$root\frontend"
& $fl run -d web-server --web-port $Port
