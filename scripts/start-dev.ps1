param(
    [string]$Root = (Split-Path -Parent $PSScriptRoot),
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$rootPath = (Resolve-Path -LiteralPath $Root).Path
$apiPath = Join-Path $rootPath "services\api"
$webPath = Join-Path $rootPath "apps\web"
$pythonPath = Join-Path $apiPath ".venv\Scripts\python.exe"
$environmentPath = Join-Path $apiPath ".env"
$packagePath = Join-Path $webPath "package.json"
$runtimePath = Join-Path $rootPath ".runtime"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python virtual environment is missing: $pythonPath. Follow README setup first."
}
if (-not (Test-Path -LiteralPath $environmentPath)) {
    throw "Environment file is missing: $environmentPath. Copy .env.example and configure it."
}
if (-not (Test-Path -LiteralPath $packagePath)) {
    throw "Frontend package.json is missing: $packagePath."
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "npm.cmd was not found. Install Node.js first."
}

if ($CheckOnly) {
    [pscustomobject]@{
        status = "ready"
        root = $rootPath
        python = $pythonPath
        environment = $environmentPath
    } | ConvertTo-Json -Compress
    exit 0
}

Get-Content -LiteralPath $environmentPath -Encoding utf8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
    $name, $value = $line.Split("=", 2)
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
}

New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null

Push-Location $apiPath
try {
    & $pythonPath -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed with exit code $LASTEXITCODE." }
}
finally {
    Pop-Location
}

$started = @()
try {
    $api = Start-Process -FilePath $pythonPath -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $apiPath -WindowStyle Hidden -PassThru
    $started += $api
    $worker = Start-Process -FilePath $pythonPath -ArgumentList "-m", "app.scans.worker" -WorkingDirectory $apiPath -WindowStyle Hidden -PassThru
    $started += $worker
    $web = Start-Process -FilePath "npm.cmd" -ArgumentList "run", "dev" -WorkingDirectory $webPath -WindowStyle Hidden -PassThru
    $started += $web

    [pscustomobject]@{
        api = $api.Id
        worker = $worker.Id
        web = $web.Id
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath "dev-processes.json") -Encoding utf8

    $deadline = (Get-Date).AddSeconds(40)
    $apiReady = $false
    $webReady = $false
    while ((Get-Date) -lt $deadline -and (-not $apiReady -or -not $webReady)) {
        if (-not $apiReady) {
            try { $apiReady = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2).StatusCode -eq 200 } catch { $apiReady = $false }
        }
        if (-not $webReady) {
            try { $webReady = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:3000" -TimeoutSec 2).StatusCode -eq 200 } catch { $webReady = $false }
        }
        if (-not $apiReady -or -not $webReady) { Start-Sleep -Milliseconds 750 }
    }
    if (-not $apiReady -or -not $webReady) {
        throw "Service startup timed out: API=$apiReady, Web=$webReady."
    }

    Write-Host "Project started:"
    Write-Host "  Web: http://127.0.0.1:3000"
    Write-Host "  API: http://127.0.0.1:8000/docs"
    Write-Host "Stop with: .\scripts\stop-dev.cmd"
}
catch {
    foreach ($process in $started) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
    throw
}
