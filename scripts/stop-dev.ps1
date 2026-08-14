param([string]$Root = (Split-Path -Parent $PSScriptRoot))

$ErrorActionPreference = "Stop"
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$processFile = Join-Path $rootPath ".runtime\dev-processes.json"
if (-not (Test-Path -LiteralPath $processFile)) {
    Write-Host "No managed development processes were found."
    exit 0
}

$processes = Get-Content -LiteralPath $processFile -Encoding utf8 | ConvertFrom-Json
foreach ($name in "api", "worker", "web") {
    $processId = $processes.$name
    if ($processId) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
}
Remove-Item -LiteralPath $processFile -Force
Write-Host "Development processes stopped."
