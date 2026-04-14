#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"
$dir = "$(Get-ProjectRoot)\frontend-public"
Assert-FileExists "$dir\node_modules" "Run bootstrap-frontend.ps1"
Set-Location $dir
npm test -- --passWithNoTests @args
