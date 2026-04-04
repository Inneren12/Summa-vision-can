param(
    [string]$AcId,
    [string]$TaskFile
)

if (-not $AcId) {
    Write-Host "Usage: .\get_ac_content.ps1 <AC_ID> [task_file]"
    exit 1
}

$sprintFiles = Get-ChildItem -Path "specs\sprints\*.md"
$acContent = $null
$actualHash = $null

foreach ($file in $sprintFiles) {
    $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8
    $pattern = '(?s)<ac-block id="' + [regex]::Escape($AcId) + '">(.*?)</ac-block>'
    $m = [regex]::Match($content, $pattern)
    
    if ($m.Success) {
        $acContent = $m.Groups[1].Value
        
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($acContent)
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        $hashBytes = $sha256.ComputeHash($bytes)
        $actualHash = ([BitConverter]::ToString($hashBytes) -replace '-','').ToLower()
        break
    }
}

if (-not $acContent) {
    Write-Host "ERROR: AC block $AcId not found in any sprint file"
    exit 1
}

if ($TaskFile) {
    if (Test-Path $TaskFile) {
        $task = Get-Content -Path $TaskFile -Raw | ConvertFrom-Json
        $expectedHash = $task.expected_hash
        
        if ($expectedHash -ne $actualHash) {
            Write-Host "ERROR: STALE_CONTEXT - AC block has been modified"
            Write-Host "Expected hash: $expectedHash"
            Write-Host "Actual hash:   $actualHash"
            exit 2
        }
    }
}

Write-Output $acContent
