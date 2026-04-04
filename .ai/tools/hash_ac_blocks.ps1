param(
    [string]$SprintFile = 'specs/sprints/sprint-1.md'
)

$content = Get-Content -Path $SprintFile -Raw -Encoding UTF8

function Get-AcBlocks {
    param([string]$fileContent)
    $pattern = '(?s)<ac-block id="(.*?)">(.*?)</ac-block>'
    $results = @{}
    $matches = [regex]::Matches($fileContent, $pattern)
    foreach ($m in $matches) {
        $results[$m.Groups[1].Value] = $m.Groups[2].Value
    }
    return $results
}

$blocks = Get-AcBlocks -fileContent $content

if ($blocks.Count -eq 0) {
    Write-Output "No AC blocks found in $SprintFile"
    exit
}

foreach ($id in $blocks.Keys) {
    $block = $blocks[$id]
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($block)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $hashBytes = $sha256.ComputeHash($bytes)
    $hashHex = [BitConverter]::ToString($hashBytes) -replace '-',''
    Write-Output "$id`t$($hashHex.ToLower())"
}
