#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"

Write-Host "=== BACKEND SMOKE TEST ===" -ForegroundColor Cyan

$root = Get-ProjectRoot
$API = "http://localhost:8000"
$pass = 0; $fail = 0

# Read admin key from .env
$adminKey = ""
$envFile = "$root\backend\.env"
if (Test-Path $envFile) {
    $line = Get-Content $envFile | Select-String '^ADMIN_API_KEY=' | Select-Object -First 1
    if ($line) { $adminKey = $line.ToString().Split('=',2)[1].Trim() }
}

function Smoke([string]$name, [string]$url, [int]$expectStatus = 200, [hashtable]$headers = @{}) {
    try {
        $params = @{ Uri = $url; TimeoutSec = 5; UseBasicParsing = $true; Method = "GET" }
        if ($headers.Count -gt 0) { $params.Headers = $headers }
        $resp = Invoke-WebRequest @params -ErrorAction Stop
        if ($resp.StatusCode -eq $expectStatus) {
            Write-OK $name; $script:pass++
        } else {
            Write-Fail "$name - expected $expectStatus got $($resp.StatusCode)"; $script:fail++
        }
    } catch {
        $code = 0
        if ($_.Exception.Response) {
            $code = [int]$_.Exception.Response.StatusCode
        }
        if ($expectStatus -ne 200 -and $code -eq $expectStatus) {
            Write-OK "$name (expected $code)"; $script:pass++
        } else {
            $msg = if ($code -gt 0) { "HTTP $code" } else { $_.Exception.Message }
            Write-Fail "$name - $msg"; $script:fail++
        }
    }
}

Smoke "Health" "$API/api/health"
Smoke "METR Calculate" "$API/api/v1/public/metr/calculate?income=47000&province=ON&family_type=single_parent&n_children=2&children_under_6=2"
Smoke "METR Curve" "$API/api/v1/public/metr/curve?province=ON&family_type=single_parent&n_children=2&children_under_6=2&step=5000"
Smoke "METR Compare" "$API/api/v1/public/metr/compare?income=47000&family_type=single_parent&n_children=2&children_under_6=2"
Smoke "Admin no key -> 401" "$API/api/v1/admin/jobs" 401
if ($adminKey) {
    Smoke "Admin with key -> 200" "$API/api/v1/admin/jobs" 200 @{"X-API-KEY" = $adminKey}
} else {
    Write-Host "  SKIP Admin happy path - no ADMIN_API_KEY in .env" -ForegroundColor DarkYellow
}
Smoke "Gallery" "$API/api/v1/public/graphics?limit=1"

Write-Host "`n=== $pass passed, $fail failed ===" -ForegroundColor $(if ($fail -eq 0) {"Cyan"} else {"Red"})
exit $(if ($fail -eq 0) {0} else {1})
