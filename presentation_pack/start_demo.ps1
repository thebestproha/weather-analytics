param(
  [switch]$Setup
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

function Stop-PortListener {
  param([int]$Port)
  $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  if ($conn) {
    $pidValue = $conn.OwningProcess
    Stop-Process -Id $pidValue -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
  }
}

$venvPy = Join-Path $root ".venv\Scripts\python.exe"
$py = $venvPy

if ($Setup -or -not (Test-Path $venvPy)) {
  Write-Host "Setting up virtual environment and dependencies..." -ForegroundColor Yellow
  Set-Location $root
  python -m venv .venv
  & $venvPy -m pip install --upgrade pip
  & $venvPy -m pip install -r (Join-Path $root "requirements_demo.txt")
}

if (-not (Test-Path $py)) {
  $py = "python"
}

$ports = @{
  Backend = 8000
  FrontOld = 5173
  FrontNew = 5174
  Compare = 5180
}

Stop-PortListener -Port $ports.Backend
Stop-PortListener -Port $ports.FrontOld
Stop-PortListener -Port $ports.FrontNew
Stop-PortListener -Port $ports.Compare

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root\\backend'; & '$py' -m uvicorn app.main:app --host 127.0.0.1 --port $($ports.Backend)"
) | Out-Null

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root\\frontend'; & '$py' -m http.server $($ports.FrontOld)"
) | Out-Null

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root\\frontend'; & '$py' -m http.server $($ports.FrontNew)"
) | Out-Null

Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root\\compare'; & '$py' -m http.server $($ports.Compare)"
) | Out-Null

Start-Sleep -Seconds 2

Write-Host "Demo services started:" -ForegroundColor Green
Write-Host "- Backend API: http://127.0.0.1:8000"
Write-Host "- Old model page (A+B): http://127.0.0.1:5173/index.html"
Write-Host "- New model page (A+C): http://127.0.0.1:5174/index_model_c.html"
Write-Host "- 3-way compare page: http://127.0.0.1:5180/side_by_side_compare.html"
Write-Host ""
Write-Host "Use stop_demo.ps1 to stop all services." -ForegroundColor Yellow
