#!/usr/bin/env pwsh
# Bootstrap backend: Python 3.12 venv + deps + .env
. "$PSScriptRoot\lib\common.ps1"

$root = Get-ProjectRoot
$backend = "$root\backend"

Write-Host "=== BACKEND BOOTSTRAP ===" -ForegroundColor Cyan

# -- Python 3.12 --
Write-Step "1/4" "Finding Python 3.12..."
$py = Get-Python312
if (-not $py) {
    Write-Fail "Python 3.12 not found (3.14 breaks pyarrow)"
    Write-Host "  Install: https://www.python.org/downloads/" -ForegroundColor DarkYellow
    exit 1
}
Write-OK "Python: $py"

# -- venv --
Write-Step "2/4" "Creating venv..."
$venv = "$backend\.venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    if ($py -eq "py -3.12") {
        py -3.12 -m venv $venv
    } else {
        & $py -m venv $venv
    }
}

$python = Get-BackendPython
$actualVer = & $python --version 2>&1
if ($actualVer -notmatch "3\.12") {
    Write-Fail "venv has $actualVer - delete $venv and retry"
    exit 1
}
Write-OK "venv: $actualVer"

# -- Dependencies from requirements-dev.txt --
Write-Step "3/4" "Installing dependencies..."
$reqFile = "$backend\requirements-dev.txt"
Assert-FileExists $reqFile "Generate it: pip freeze > requirements-dev.txt from a working env"
& "$venv\Scripts\pip.exe" install --quiet --upgrade pip
& "$venv\Scripts\pip.exe" install --quiet -r $reqFile

& $python -c "import fastapi, sqlalchemy, pytest, polars, pyarrow" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Critical imports failed"
    exit 1
}
Write-OK "All dependencies installed"

# -- .env --
Write-Step "4/4" "Checking .env..."
$envFile = "$backend\.env"
if (-not (Test-Path $envFile)) {
    @"
DATABASE_URL=sqlite+aiosqlite:///./summa_dev.db
ADMIN_API_KEY=dev-secret-key-change-in-production
S3_BUCKET=summa-dev
S3_ENDPOINT_URL=http://localhost:9000
CDN_BASE_URL=http://localhost:9000/summa-dev
PUBLIC_SITE_URL=http://localhost:3000
TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA
"@ | Out-File -Encoding utf8 $envFile
    Write-OK ".env created with dev defaults"
} else {
    Write-OK ".env exists"
}

Write-Host "`n=== BACKEND READY ===" -ForegroundColor Cyan
