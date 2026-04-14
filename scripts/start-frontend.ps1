#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"

$root = Get-ProjectRoot
$dir = "$root\frontend-public"

Assert-FileExists "$dir\node_modules" "Run .\scripts\bootstrap-frontend.ps1"
Assert-PortFree 3000 "Next.js"

Write-Host "Starting Next.js -> http://localhost:3000" -ForegroundColor Cyan
Write-Host "Ctrl+C to stop`n" -ForegroundColor DarkGray

Set-Location $dir
npm run dev
