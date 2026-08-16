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
$nextEntryPath = Join-Path $webPath "node_modules\next\dist\bin\next"
$runtimePath = Join-Path $rootPath ".runtime"
$heartbeatPath = Join-Path $apiPath ".runtime\worker-heartbeat.json"
$logFileNames = @("api.out.log", "api.err.log", "worker.out.log", "worker.err.log", "web.out.log", "web.err.log")

function Get-ListeningProcessId([int]$Port) {
    foreach ($line in (& netstat.exe -ano -p tcp)) {
        if ($line -match "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$") {
            return [int]$Matches[1]
        }
    }
    return $null
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python virtual environment is missing: $pythonPath. Follow README setup first."
}
if (-not (Test-Path -LiteralPath $environmentPath)) {
    throw "Environment file is missing: $environmentPath. Copy .env.example and configure it."
}
if (-not (Test-Path -LiteralPath $packagePath)) {
    throw "Frontend package.json is missing: $packagePath."
}
$nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $nodeCommand) {
    throw "node.exe was not found. Install Node.js first."
}
if (-not (Test-Path -LiteralPath $nextEntryPath)) {
    throw "Next.js runtime is missing: $nextEntryPath. Run npm install first."
}

if ($CheckOnly) {
    [pscustomobject]@{
        status = "ready"
        root = $rootPath
        python = $pythonPath
        environment = $environmentPath
        workerHeartbeat = $heartbeatPath
        logFiles = $logFileNames
        webExecutable = $nodeCommand.Source
        webEntryPoint = $nextEntryPath
    } | ConvertTo-Json -Compress
    exit 0
}

foreach ($requiredPort in 8000, 3000) {
    $ownerId = Get-ListeningProcessId -Port $requiredPort
    if ($ownerId) {
        throw "Port $requiredPort is already in use by PID $ownerId. Stop the existing project before starting a new one."
    }
}

Get-Content -LiteralPath $environmentPath -Encoding utf8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
    $name, $value = $line.Split("=", 2)
    [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
}

# Some Windows launchers provide both Path and PATH. Start-Process builds a
# case-insensitive environment dictionary and fails when both spellings exist.
$processPath = [Environment]::GetEnvironmentVariable("Path", "Process")
[Environment]::SetEnvironmentVariable("PATH", $null, "Process")
[Environment]::SetEnvironmentVariable("Path", $processPath, "Process")

New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $heartbeatPath) -Force | Out-Null
Remove-Item -LiteralPath $heartbeatPath -Force -ErrorAction SilentlyContinue

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
    $api = Start-Process -FilePath $pythonPath -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" -WorkingDirectory $apiPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimePath "api.out.log") -RedirectStandardError (Join-Path $runtimePath "api.err.log") -PassThru
    $started += $api
    $worker = Start-Process -FilePath $pythonPath -ArgumentList "-m", "app.scans.worker" -WorkingDirectory $apiPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimePath "worker.out.log") -RedirectStandardError (Join-Path $runtimePath "worker.err.log") -PassThru
    $started += $worker
    $web = Start-Process -FilePath $nodeCommand.Source -ArgumentList $nextEntryPath, "dev", "--webpack", "--port", "3000" -WorkingDirectory $webPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimePath "web.out.log") -RedirectStandardError (Join-Path $runtimePath "web.err.log") -PassThru
    $started += $web

    [pscustomobject]@{
        api = $api.Id
        worker = $worker.Id
        web = $web.Id
        apiLauncher = $api.Id
        webLauncher = $web.Id
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath "dev-processes.json") -Encoding utf8

    $deadline = (Get-Date).AddSeconds(40)
    $apiReady = $false
    $webReady = $false
    $workerReady = $false
    while ((Get-Date) -lt $deadline -and (-not $apiReady -or -not $webReady -or -not $workerReady)) {
        if ($api.HasExited) { throw "API exited during startup. See .runtime\api.err.log." }
        if ($worker.HasExited) { throw "Worker exited during startup. See .runtime\worker.err.log." }
        if ($web.HasExited) { throw "Web exited during startup. See .runtime\web.err.log." }
        if (-not $apiReady) {
            try { $apiReady = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2).StatusCode -eq 200 } catch { $apiReady = $false }
        }
        if (-not $webReady) {
            try { $webReady = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:3000" -TimeoutSec 2).StatusCode -eq 200 } catch { $webReady = $false }
        }
        if (-not $workerReady -and (Test-Path -LiteralPath $heartbeatPath)) {
            $workerReady = (Get-Item -LiteralPath $heartbeatPath).LastWriteTime -ge $worker.StartTime
        }
        if (-not $apiReady -or -not $webReady -or -not $workerReady) { Start-Sleep -Milliseconds 750 }
    }
    if (-not $apiReady -or -not $webReady -or -not $workerReady) {
        throw "Service startup timed out: API=$apiReady, Web=$webReady, Worker=$workerReady."
    }

    $apiListenerId = Get-ListeningProcessId -Port 8000
    $webListenerId = Get-ListeningProcessId -Port 3000
    if (-not $apiListenerId -or -not $webListenerId) {
        throw "Service ports were not owned after startup: API=$apiListenerId, Web=$webListenerId."
    }
    [pscustomobject]@{
        api = $apiListenerId
        worker = $worker.Id
        web = $webListenerId
        apiLauncher = $api.Id
        webLauncher = $web.Id
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath "dev-processes.json") -Encoding utf8

    Write-Host "Project started:"
    Write-Host "  Web: http://127.0.0.1:3000"
    Write-Host "  API: http://127.0.0.1:8000/docs"
    Write-Host "Stop with: .\scripts\stop-dev.cmd"
}
catch {
    $cleanupIds = @($started | ForEach-Object { $_.Id })
    $cleanupIds += Get-ListeningProcessId -Port 8000
    $cleanupIds += Get-ListeningProcessId -Port 3000
    foreach ($cleanupId in ($cleanupIds | Where-Object { $_ } | Sort-Object -Unique)) {
        Stop-Process -Id $cleanupId -Force -ErrorAction SilentlyContinue
    }
    throw
}
