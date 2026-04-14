#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"
$fl = Get-FlutterCmd
if (-not $fl) { Write-Fail "Flutter not found. Run bootstrap-flutter.ps1"; exit 1 }
Set-Location "$(Get-ProjectRoot)\frontend"
& $fl test @args
