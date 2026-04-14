#!/usr/bin/env pwsh
# Bootstrap backend: Python 3.12 venv + Poetry deps + .env
param(
    [switch]$Lite,   # SQLite, no Docker
    [switch]$Full    # Postgres + MinIO (requires Docker)
)

. "$PSScriptRoot\lib\common.ps1"

$root = Get-ProjectRoot
$backend = "$root\backend"

if (-not $Lite -and -not $Full) { $Lite = $true }

Write-Host "=== BACKEND BOOTSTRAP ($( if ($Full) {'Full'} else {'Lite'} )) ===" -ForegroundColor Cyan

# -- 1. Python 3.12 --
Write-Step "1/5" "Finding Python 3.12..."
$py = Get-Python312
if (-not $py) {
    Write-Fail "Python 3.12 not found (3.14 breaks pyarrow)"
    Write-Host "  Install: https://www.python.org/downloads/" -ForegroundColor DarkYellow
    exit 1
}
Write-OK "Python: $py"

# -- 2. venv --
Write-Step "2/5" "Setting up venv..."
$venv = "$backend\.venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    & $py -m venv $venv
}
$venvPython = Get-BackendPython
$actualVer = & $venvPython --version 2>&1
if ($actualVer -notmatch "3\.12") {
    Write-Fail "venv has $actualVer - delete $venv and retry"
    exit 1
}
Write-OK "venv: $actualVer"

# -- 3. Poetry (installed into venv, not global) --
Write-Step "3/5" "Checking Poetry..."
$poetryInVenv = "$venv\Scripts\poetry.exe"
if (-not (Test-Path $poetryInVenv)) {
    Write-Host "  Installing Poetry into venv..." -ForegroundColor DarkGray
    & "$venv\Scripts\pip.exe" install --quiet poetry
}

# -- 4. Install deps via Poetry --
Write-Step "4/5" "Installing dependencies..."
Set-Location $backend

$origPath = $env:PATH
try {
    $env:POETRY_VIRTUALENVS_IN_PROJECT = "true"
    $env:POETRY_VIRTUALENVS_CREATE = "false"
    $env:VIRTUAL_ENV = $venv
    $env:PATH = "$venv\Scripts;$env:PATH"

    $poetryOutput = & $poetryInVenv install --no-interaction 2>&1
    $poetryExit = $LASTEXITCODE

    $poetryOutput | ForEach-Object {
        if ($_ -match "Installing|Updating") { Write-Host "    $_" -ForegroundColor DarkGray }
    }

    if ($poetryExit -ne 0) {
        Write-Fail "poetry install failed. Full output:"
        $poetryOutput | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
        exit 1
    }

    # Verify critical runtime imports only
    & $venvPython -c "import fastapi, sqlalchemy, structlog" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Critical imports failed"
        exit 1
    }
    Write-OK "Dependencies installed"
} finally {
    $env:PATH = $origPath
}

# -- 5. .env --
Write-Step "5/5" "Checking .env..."
$envFile = "$backend\.env"
if (-not (Test-Path $envFile)) {
    if ($Full) {
        # S3 var names match backend/src/core/config.py Settings class:
        # s3_access_key_id / s3_secret_access_key (Pydantic lower-case -> env upper-case)
        @"
DATABASE_URL=postgresql+asyncpg://summa:summa@localhost:5432/summa_dev
ADMIN_API_KEY=dev-secret-key-change-in-production
S3_BUCKET=summa-dev
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
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
STORAGE_BACKEND=local
LOCAL_STORAGE_DIR=./storage_local
CDN_BASE_URL=http://localhost:8000/static
PUBLIC_SITE_URL=http://localhost:3000
TURNSTILE_SECRET_KEY=1x0000000000000000000000000000000AA
"@ | Out-File -Encoding utf8 $envFile
        Write-OK ".env created (Lite: SQLite + local storage, no Docker)"
    }
} else {
    # Show current mode
    $dbLine = (Get-Content $envFile | Select-String 'DATABASE_URL').ToString()
    $mode = if ($dbLine -match "sqlite") { "Lite" } else { "Full" }
    Write-OK ".env exists ($mode mode)"
}

Set-Location $root
Write-Host "`n=== BACKEND READY ===" -ForegroundColor Cyan
