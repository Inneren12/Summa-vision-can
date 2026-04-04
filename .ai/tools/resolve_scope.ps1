param(
    [string]$TaskFile
)

if (-not $TaskFile) {
    Write-Host "Usage: .\resolve_scope.ps1 <TASK_FILE>"
    exit 1
}

$task = Get-Content -Path $TaskFile -Raw | ConvertFrom-Json

Write-Output "=== Allowed Scope ==="
if ($task.touches.include) { $task.touches.include }

Write-Output "=== Excluded ==="
if ($task.touches.exclude -and $task.touches.exclude.Count -gt 0) { $task.touches.exclude } else { "(none)" }

Write-Output "=== Dependencies ==="
if ($task.depends_on -and $task.depends_on.Count -gt 0) { $task.depends_on } else { "(none)" }
