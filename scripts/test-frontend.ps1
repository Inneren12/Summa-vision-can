#!/usr/bin/env pwsh
. "$PSScriptRoot\lib\common.ps1"
Set-Location "$(Get-ProjectRoot)\frontend-public"
npm test -- --passWithNoTests @args
