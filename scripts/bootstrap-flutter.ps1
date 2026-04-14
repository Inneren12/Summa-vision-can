#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"

$root = Get-ProjectRoot

Write-Host "=== FLUTTER BOOTSTRAP ===" -ForegroundColor Cyan

Write-Step "1/2" "Finding Flutter SDK..."
$fl = Get-FlutterCmd
if (-not $fl) {
    Write-Fail "Flutter SDK not found"
    Write-Host "  Searched: C:\flutter\flutter\bin, C:\flutter\bin, FLUTTER_ROOT" -ForegroundColor DarkYellow
    exit 1
}
$flDir = Split-Path $fl -Parent
$flVer = (& $fl --version 2>&1 | Select-Object -First 1)
Write-OK "Flutter: $flVer"
Write-Host "    Path: $fl" -ForegroundColor DarkGray

Write-Step "2/2" "pub get..."
Set-Location "$root\frontend"
& $fl pub get 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail "flutter pub get failed"
    exit 1
}
Write-OK "Dependencies resolved"

Set-Location $root
Write-Host "`n=== FLUTTER READY ===" -ForegroundColor Cyan
Write-Host "  SDK: $flDir" -ForegroundColor White

# Check if flutter is in persistent PATH
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notmatch [regex]::Escape($flDir)) {
    Write-Host "  WARNING: Flutter NOT in permanent PATH" -ForegroundColor DarkYellow
    Write-Host "  Add to User PATH: $flDir" -ForegroundColor DarkYellow
    Write-Host "  Or set env: FLUTTER_ROOT=$(Split-Path $flDir -Parent)" -ForegroundColor DarkYellow
}
