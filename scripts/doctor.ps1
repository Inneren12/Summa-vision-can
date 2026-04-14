#!/usr/bin/env pwsh
# Full environment diagnostic - answers "why isn't it working?" in 5 seconds
. "$PSScriptRoot\lib\common.ps1"

Write-Host "=== SUMMA VISION DOCTOR ===" -ForegroundColor Cyan
$issues = 0; $warnings = 0

# --- Mandatory ---
Write-Host "`n  Mandatory:" -ForegroundColor White

$py = Get-Python312
if ($py) { Write-OK "Python 3.12: $py" } else { Write-Fail "Python 3.12: NOT FOUND"; $issues++ }

$bp = Get-BackendPython
if ($bp) { Write-OK "Backend venv: $(& $bp --version 2>&1)" } else { Write-Fail "Backend venv: MISSING"; $issues++ }

$root = Get-ProjectRoot
$envFile = "$root\backend\.env"
if (Test-Path $envFile) {
    $dbLine = (Get-Content $envFile | Select-String 'DATABASE_URL').ToString()
    $storLine = Get-Content $envFile | Select-String 'STORAGE_BACKEND'
    $dbMode = if ($dbLine -match "sqlite") { "SQLite" } else { "Postgres" }
    $stMode = if ($storLine -and $storLine -match "local") { "local" } elseif ($dbLine -match "sqlite") { "local (implied)" } else { "S3/MinIO" }
    Write-OK "Backend .env: DB=$dbMode, Storage=$stMode"
} else { Write-Fail "Backend .env: MISSING"; $issues++ }

if (Get-Command node -ErrorAction SilentlyContinue) { Write-OK "Node.js: $(node --version)" } else { Write-Fail "Node.js: NOT FOUND"; $issues++ }
if (Get-Command npm -ErrorAction SilentlyContinue) { Write-OK "npm: $(npm --version)" } else { Write-Fail "npm: NOT FOUND"; $issues++ }

if (Test-Path "$root\frontend-public\node_modules") { Write-OK "Frontend deps: installed" } else { Write-Fail "Frontend deps: MISSING"; $issues++ }

foreach ($p in @(@(8000,"Backend"), @(3000,"Frontend"))) {
    if (Test-PortFree $p[0]) { Write-OK "Port $($p[0]): free ($($p[1]))" }
    else { Write-Fail "Port $($p[0]): OCCUPIED ($($p[1]))"; $issues++ }
}

# --- Optional ---
Write-Host "`n  Optional:" -ForegroundColor White

$fl = Get-FlutterCmd
if ($fl) {
    Write-OK "Flutter: $fl"
    if (Test-PortFree 8082) { Write-OK "Port 8082: free (Flutter)" }
    else { Write-Host "  !!  Port 8082: occupied" -ForegroundColor DarkYellow; $warnings++ }
} else {
    Write-Host "  --  Flutter: not found (admin panel won't run)" -ForegroundColor DarkGray
    $warnings++
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    try { docker info 2>&1 | Out-Null; Write-OK "Docker: running" }
    catch { Write-Host "  !!  Docker: installed but not running" -ForegroundColor DarkYellow; $warnings++ }
} else {
    Write-Host "  --  Docker: not installed (needed for Full mode)" -ForegroundColor DarkGray
}

Write-Host "`n=== $issues issue(s), $warnings warning(s) ===" -ForegroundColor $(if ($issues -eq 0) {"Cyan"} else {"Red"})
# Exit code only counts mandatory issues
exit $issues
