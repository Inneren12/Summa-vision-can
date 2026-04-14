#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"

Write-Host "=== BACKEND SMOKE TEST ===" -ForegroundColor Cyan

$API = "http://localhost:8000"
$pass = 0; $fail = 0

function Smoke([string]$name, [string]$url, [int]$expectStatus = 200) {
    try {
        $resp = Invoke-WebRequest $url -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($resp.StatusCode -eq $expectStatus) {
            Write-OK $name; $script:pass++
        } else {
            Write-Fail "$name - got $($resp.StatusCode)"; $script:fail++
        }
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($expectStatus -and $code -eq $expectStatus) {
            Write-OK "$name (expected $code)"; $script:pass++
        } else {
            Write-Fail "$name - $($_.Exception.Message)"; $script:fail++
        }
    }
}

Smoke "Health" "$API/api/health"
Smoke "METR Calculate" "$API/api/v1/public/metr/calculate?income=47000&province=ON&family_type=single_parent&n_children=2&children_under_6=2"
Smoke "METR Curve" "$API/api/v1/public/metr/curve?province=ON&family_type=single_parent&n_children=2&children_under_6=2&step=5000"
Smoke "METR Compare" "$API/api/v1/public/metr/compare?income=47000&family_type=single_parent&n_children=2&children_under_6=2"
Smoke "Admin no key" "$API/api/v1/admin/jobs" 401
Smoke "Gallery" "$API/api/v1/public/graphics?limit=1"

Write-Host "`nResults: $pass passed, $fail failed" -ForegroundColor $(if ($fail -eq 0) {"Cyan"} else {"Red"})
exit $(if ($fail -eq 0) {0} else {1})
