#!/usr/bin/env pwsh
# Bootstrap backend: Python 3.12 venv + Poetry deps + .env
param(
    [switch]$Lite,   # SQLite, no Docker
    [switch]$Full    # Postgres + MinIO (requires Docker)
)

. "$PSScriptRoot\lib\common.ps1"

# Default to Lite if neither specified
if (-not $Lite -and -not $Full) { $Lite = $true }

$root = Get-ProjectRoot
$backend = "$root\backend"

Write-Host "=== BACKEND BOOTSTRAP ===" -ForegroundColor Cyan

# -- Python 3.12 --
Write-Step "1/5" "Finding Python 3.12..."
$PYTHON = Get-Python312
if (-not $PYTHON) {
    Write-Fail "Python 3.12 not found (3.14 breaks pyarrow)"
    Write-Host "  Install: https://www.python.org/downloads/" -ForegroundColor DarkYellow
    exit 1
}
Write-OK "Python: $PYTHON"

# -- venv --
Write-Step "2/5" "Creating venv..."
$venv = "$backend\.venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    & $PYTHON -m venv $venv
}

$python = Get-BackendPython
$actualVer = & $python --version 2>&1
if ($actualVer -notmatch "3\.12") {
    Write-Fail "venv has $actualVer - delete $venv and retry"
    exit 1
}
Write-OK "venv: $actualVer"

# -- Install Poetry if missing --
Write-Step "3/5" "Checking Poetry..."
$poetryCmd = Get-Command poetry -ErrorAction SilentlyContinue
if (-not $poetryCmd) {
    Write-Host "  Installing Poetry..." -ForegroundColor Yellow
    & $PYTHON -m pip install --quiet poetry
}

# -- Install dependencies via Poetry --
Write-Step "4/5" "Installing dependencies (Poetry)..."
Set-Location $backend
# Tell Poetry to use our venv, not create its own
$env:POETRY_VIRTUALENVS_IN_PROJECT = "true"
$env:POETRY_VIRTUALENVS_CREATE = "false"

# Activate venv so Poetry installs into it
$env:VIRTUAL_ENV = $venv
$origPath = $env:PATH
$env:PATH = "$venv\Scripts;$env:PATH"

poetry install --no-interaction 2>&1 | ForEach-Object {
    if ($_ -match "Installing|Updating") { Write-Host "  $_" -ForegroundColor DarkGray }
}
if ($LASTEXITCODE -ne 0) {
    Write-Fail "poetry install failed"
    exit 1
}

$env:PATH = $origPath

& $python -c "import fastapi, sqlalchemy, pytest, polars, pyarrow" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Critical imports failed"
    exit 1
}
Write-OK "All dependencies installed"

# -- .env --
Write-Step "5/5" "Checking .env..."
$envFile = "$backend\.env"
if (-not (Test-Path $envFile)) {
    if ($Full) {
        @"
DATABASE_URL=postgresql+asyncpg://summa:summa@localhost:5432/summa_dev
ADMIN_API_KEY=dev-secret-key-change-in-production
S3_BUCKET=summa-dev
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
CDN_BASE_URL=http://localhost:9000/summa-dev
PUBLIC_SITE_URL=http://localhost:3000
TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA
"@ | Out-File -Encoding utf8 $envFile
        Write-OK ".env created (Full: Postgres + MinIO)"
        Write-Host "  Run: docker compose -f docker-compose.dev.yml up -d" -ForegroundColor DarkYellow
    } else {
        @"
DATABASE_URL=sqlite+aiosqlite:///./summa_dev.db
ADMIN_API_KEY=dev-secret-key-change-in-production
S3_BUCKET=summa-dev
S3_ENDPOINT_URL=http://localhost:9000
CDN_BASE_URL=http://localhost:9000/summa-dev
PUBLIC_SITE_URL=http://localhost:3000
TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA
"@ | Out-File -Encoding utf8 $envFile
        Write-OK ".env created (Lite: SQLite, no Docker)"
    }
} else {
    Write-OK ".env exists"
}

Write-Host "`n=== BACKEND READY ===" -ForegroundColor Cyan
