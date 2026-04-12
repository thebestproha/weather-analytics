param(
  [switch]$OpenPages
)

$ErrorActionPreference = "Stop"

function Stop-PortListener {
  param([int]$Port)

  $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($conn) {
    $owningPid = $conn.OwningProcess
    Stop-Process -Id $owningPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
    Write-Host "Stopped existing listener on port $Port (PID $owningPid)"
  }
}

function Wait-Endpoint {
  param(
    [string]$Url,
    [int]$MaxAttempts = 20,
    [int]$DelayMs = 300
  )

  for ($i = 0; $i -lt $MaxAttempts; $i++) {
    try {
      $resp = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
      if ($resp.StatusCode -ge 200 -and $resp.StatusCode -lt 500) {
        return $true
      }
    }
    catch {
      # Backend may still be booting.
    }
    Start-Sleep -Milliseconds $DelayMs
  }

  return $false
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$compareDir = Join-Path $projectRoot "weather_model_b_ml_clone"
$pythonExe = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
  throw "Python executable not found at: $pythonExe"
}
if (-not (Test-Path $compareDir)) {
  throw "Compare folder not found at: $compareDir"
}

$ports = @{
  Backend = 8000
  OldPage = 5173
  NewPage = 5174
  ComparePage = 5180
}

# Clean start on fixed ports
Stop-PortListener -Port $ports.Backend
Stop-PortListener -Port $ports.OldPage
Stop-PortListener -Port $ports.NewPage
Stop-PortListener -Port $ports.ComparePage

# Start backend API
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$backendDir'; & '$pythonExe' -m uvicorn app.main:app --host 127.0.0.1 --port $($ports.Backend)"
) | Out-Null

# Start old model page
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$frontendDir'; & '$pythonExe' -m http.server $($ports.OldPage)"
) | Out-Null

# Start new model page (same frontend directory, different port)
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$frontendDir'; & '$pythonExe' -m http.server $($ports.NewPage)"
) | Out-Null

# Start 3-way compare page
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$compareDir'; & '$pythonExe' -m http.server $($ports.ComparePage) --directory '$compareDir'"
) | Out-Null

if (-not (Wait-Endpoint -Url "http://127.0.0.1:$($ports.Backend)/")) {
  throw "Backend API did not become ready on port $($ports.Backend)."
}

$urls = @{
  "Old Model Page" = "http://127.0.0.1:$($ports.OldPage)/index.html"
  "Three-Way Compare Page" = "http://127.0.0.1:$($ports.ComparePage)/side_by_side_compare.html"
  "New Model C Page" = "http://127.0.0.1:$($ports.NewPage)/index_model_c.html"
  "Backend API" = "http://127.0.0.1:$($ports.Backend)"
}

$cacheBust = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$openUrls = @{
  "Old Model Page" = "$($urls['Old Model Page'])?cb=$cacheBust"
  "Three-Way Compare Page" = "$($urls['Three-Way Compare Page'])?cb=$cacheBust"
  "New Model C Page" = "$($urls['New Model C Page'])?cb=$cacheBust"
}

Write-Host ""
Write-Host "Started services:" -ForegroundColor Green
$urls.GetEnumerator() | ForEach-Object {
  Write-Host ("- {0}: {1}" -f $_.Key, $_.Value)
}

if ($OpenPages) {
  Start-Process $openUrls["Old Model Page"]
  Start-Process $openUrls["Three-Way Compare Page"]
  Start-Process $openUrls["New Model C Page"]
  Write-Host "Opened pages with cache-bust token: $cacheBust" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Use -OpenPages to auto-open all three pages in browser." -ForegroundColor Yellow
