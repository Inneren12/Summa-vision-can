#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"

$root = Get-ProjectRoot
$fl = Get-FlutterCmd

if (-not $fl) {
    Write-Fail "Flutter not found. Run: .\scripts\bootstrap-flutter.ps1"
    exit 1
}

Assert-PortFree 8082 "Flutter web-server"

Write-Host "Starting Flutter web-server on :8082..." -ForegroundColor Cyan
Write-Host "Open URL manually in browser (auto-launch disabled)" -ForegroundColor DarkYellow
Write-Host "Ctrl+C to stop`n" -ForegroundColor DarkGray

Set-Location "$root\frontend"
flutter run -d web-server --web-port 8082
