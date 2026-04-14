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
    .SYNOPSIS Find Python 3.12 interpreter. Returns path or $null.
    #>
    # Try py launcher
    try {
        $ver = py -3.12 --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $ver -match "3\.12") { return "py -3.12" }
    } catch {}

    # Try common install locations
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Python312\python.exe",
        "C:\Python\3.12\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $v = & $c --version 2>&1
            if ($v -match "3\.12") { return $c }
        }
    }

    # Try generic python in PATH
    try {
        $ver = python --version 2>&1
        if ($ver -match "3\.12") { return "python" }
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
    .SYNOPSIS Find flutter command. Fixes PATH if needed. Returns command name or $null.
    #>
    if (Get-Command flutter -ErrorAction SilentlyContinue) { return "flutter" }

    # Known locations
    $searchPaths = @(
        "C:\flutter\flutter\bin",
        "C:\flutter\bin",
        "$env:LOCALAPPDATA\flutter\bin",
        "$env:USERPROFILE\flutter\bin"
    )

    # Also check FLUTTER_ROOT env var
    if ($env:FLUTTER_ROOT -and (Test-Path "$env:FLUTTER_ROOT\bin\flutter.bat")) {
        $searchPaths = @("$env:FLUTTER_ROOT\bin") + $searchPaths
    }

    foreach ($p in $searchPaths) {
        if (Test-Path "$p\flutter.bat") {
            $env:PATH = "$p;$env:PATH"
            Write-Host "  [PATH] Added $p" -ForegroundColor DarkYellow
            return "flutter"
        }
    }

    return $null
}

function Test-PortFree([int]$port) {
    <#
    .SYNOPSIS Returns $true if port is free
    #>
    try {
        $listener = [System.Net.Sockets.TcpClient]::new()
        $listener.Connect("127.0.0.1", $port)
        $listener.Close()
        return $false  # port is occupied
    } catch {
        return $true   # port is free
    }
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
