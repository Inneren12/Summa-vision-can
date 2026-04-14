#!/usr/bin/env pwsh
# Full environment diagnostic - answers "why isn't it working?" in 5 seconds
. "$PSScriptRoot\lib\common.ps1"

Write-Host "=== SUMMA VISION DOCTOR ===" -ForegroundColor Cyan
$issues = 0

# Python 3.12
$py = Get-Python312
if ($py) { Write-OK "Python 3.12: $py" }
else { Write-Fail "Python 3.12: NOT FOUND"; $issues++ }

# Backend venv
$bp = Get-BackendPython
if ($bp) {
    $v = & $bp --version 2>&1
    Write-OK "Backend venv: $bp ($v)"
} else { Write-Fail "Backend venv: NOT FOUND (.venv missing)"; $issues++ }

# Backend .env + mode
$root = Get-ProjectRoot
$envFile = "$root\backend\.env"
if (Test-Path $envFile) {
    $dbLine = Get-Content $envFile | Select-String 'DATABASE_URL'
    $mode = if ($dbLine -match "sqlite") { "Lite (SQLite)" } else { "Full (Postgres)" }
    Write-OK "Backend .env: $mode"
} else {
    Write-Fail "Backend .env: MISSING"
    $issues++
}

# Node.js
if (Get-Command node -ErrorAction SilentlyContinue) { Write-OK "Node.js: $(node --version)" }
else { Write-Fail "Node.js: NOT FOUND"; $issues++ }

# npm
if (Get-Command npm -ErrorAction SilentlyContinue) { Write-OK "npm: $(npm --version)" }
else { Write-Fail "npm: NOT FOUND"; $issues++ }

# Frontend node_modules
if (Test-Path "$root\frontend-public\node_modules") { Write-OK "Frontend deps: installed" }
else { Write-Fail "Frontend deps: node_modules MISSING"; $issues++ }

# Flutter - show full path
$fl = Get-FlutterCmd
if ($fl) { Write-OK "Flutter: $fl" }
else { Write-Fail "Flutter: NOT FOUND"; $issues++ }

# Ports
foreach ($p in @(@(8000,"Backend"), @(3000,"Frontend"), @(8082,"Flutter"))) {
    if (Test-PortFree $p[0]) { Write-OK "Port $($p[0]): free ($($p[1]))" }
    else { Write-Fail "Port $($p[0]): OCCUPIED ($($p[1]))"; $issues++ }
}

# Docker (optional)
if (Get-Command docker -ErrorAction SilentlyContinue) {
    try { docker info 2>&1 | Out-Null; Write-OK "Docker: running" }
    catch { Write-Host "  !!  Docker: installed but not running" -ForegroundColor DarkYellow }
} else { Write-Host "  --  Docker: not installed (optional)" -ForegroundColor DarkGray }

Write-Host "`n=== $issues issue(s) found ===" -ForegroundColor $(if ($issues -eq 0) {"Cyan"} else {"Red"})
exit $issues
