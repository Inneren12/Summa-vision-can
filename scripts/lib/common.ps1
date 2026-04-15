# Shared functions for all Summa Vision scripts
# Usage: . "$PSScriptRoot\lib\common.ps1"  (from scripts/ directory)
#    or: . "$PSScriptRoot\..\lib\common.ps1" (if needed from subdirectory)

function Get-ProjectRoot {
    # scripts/lib/common.ps1 -> project root is two levels up
    $scriptDir = $PSScriptRoot
    if ($scriptDir -match "lib$") {
        return Split-Path -Parent (Split-Path -Parent $scriptDir)
    }
    return Split-Path -Parent $scriptDir
}

function Get-Python312 {
    <#
    .SYNOPSIS Returns full path to Python 3.12 executable, or $null.
    #>
    # py launcher
    try {
        $output = py -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $path = ($output | Select-Object -Last 1).Trim()
            if ((Test-Path $path) -and (& $path --version 2>&1) -match "3\.12") {
                return $path
            }
        }
    } catch {}

    # Known locations
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Python312\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $v = & $c --version 2>&1
            if ($v -match "3\.12") { return $c }
        }
    }

    # Generic python
    try {
        $v = python --version 2>&1
        if ($v -match "3\.12") {
            $p = (python -c "import sys; print(sys.executable)" 2>$null | Select-Object -Last 1).Trim()
            if (Test-Path $p) { return $p }
        }
    } catch {}

    return $null
}

function Get-BackendPython {
    <#
    .SYNOPSIS Returns path to backend venv python.exe
    #>
    $root = Get-ProjectRoot
    $p = "$root\backend\.venv\Scripts\python.exe"
    if (Test-Path $p) { return $p }
    return $null
}

function Get-FlutterCmd {
    <#
    .SYNOPSIS Returns full path to flutter.bat, or $null. Does NOT modify PATH.
    #>
    $existing = Get-Command flutter -ErrorAction SilentlyContinue
    if ($existing) { return $existing.Source }

    $searchPaths = @(
        "C:\flutter\flutter\bin",
        "C:\flutter\bin",
        "$env:LOCALAPPDATA\flutter\bin",
        "$env:USERPROFILE\flutter\bin"
    )
    if ($env:FLUTTER_ROOT) {
        $searchPaths = @("$env:FLUTTER_ROOT\bin") + $searchPaths
    }

    foreach ($p in $searchPaths) {
        $bat = "$p\flutter.bat"
        if (Test-Path $bat) { return $bat }
    }
    return $null
}

function Test-PortFree([int]$port) {
    <#
    .SYNOPSIS Returns $true if port is free
    #>
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    return ($null -eq $connections -or $connections.Count -eq 0)
}

function Assert-PortFree([int]$port, [string]$service) {
    if (-not (Test-PortFree $port)) {
        Write-Host "ERROR: Port $port is already in use (needed for $service)" -ForegroundColor Red
        Write-Host "  Kill the process: netstat -ano | findstr :$port" -ForegroundColor DarkYellow
        exit 1
    }
}

function Write-Step([string]$step, [string]$message) {
    Write-Host "  [$step] $message" -ForegroundColor Yellow
}

function Write-OK([string]$message) {
    Write-Host "  OK  $message" -ForegroundColor Green
}

function Write-Fail([string]$message) {
    Write-Host "  FAIL $message" -ForegroundColor Red
}

function Assert-FileExists([string]$path, [string]$hint) {
    if (-not (Test-Path $path)) {
        Write-Host "ERROR: $path not found" -ForegroundColor Red
        if ($hint) { Write-Host "  $hint" -ForegroundColor DarkYellow }
        exit 1
    }
}

function Get-HostPowerShell {
    $pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($pwsh) { return $pwsh.Source }

    $ps = Get-Command powershell.exe -ErrorAction SilentlyContinue
    if ($ps) { return $ps.Source }

    throw "Neither pwsh nor powershell.exe is available in PATH."
}