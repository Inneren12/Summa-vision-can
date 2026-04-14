#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"

$root = Get-ProjectRoot
$dir = "$root\frontend-public"

Write-Host "=== FRONTEND BOOTSTRAP ===" -ForegroundColor Cyan

Write-Step "1/3" "Checking Node.js..."
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Fail "Node.js not found. Install: https://nodejs.org"
    exit 1
}
Write-OK "Node: $(node --version)"

Write-Step "2/3" "npm install..."
Set-Location $dir
if (-not (Test-Path "node_modules")) { npm install --silent } else { Write-OK "node_modules exists" }

Write-Step "3/3" ".env.local..."
if (-not (Test-Path ".env.local")) {
    "NEXT_PUBLIC_API_URL=http://localhost:8000" | Out-File -Encoding utf8 ".env.local"
    Write-OK "created"
} else { Write-OK "exists" }

Set-Location $root
Write-Host "`n=== FRONTEND READY ===" -ForegroundColor Cyan
