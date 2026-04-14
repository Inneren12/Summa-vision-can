#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"

$root = Get-ProjectRoot
$dir = "$root\frontend"

Write-Host "=== FLUTTER BOOTSTRAP ===" -ForegroundColor Cyan

Write-Step "1/2" "Finding Flutter SDK..."
$fl = Get-FlutterCmd
if (-not $fl) {
    Write-Fail "Flutter not found"
    Write-Host "  Set FLUTTER_ROOT or add flutter/bin to PATH" -ForegroundColor DarkYellow
    exit 1
}
Write-OK "$(flutter --version 2>&1 | Select-Object -First 1)"

Write-Step "2/2" "pub get..."
Set-Location $dir
flutter pub get 2>&1 | Out-Null
Write-OK "Dependencies resolved"

Set-Location $root
Write-Host "`n=== FLUTTER READY ===" -ForegroundColor Cyan
