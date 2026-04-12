$ports = 8000, 5173, 5174, 5180
foreach ($p in $ports) {
  $conn = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
  if ($conn) {
    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    Write-Host "Stopped port $p (PID $($conn.OwningProcess))"
  } else {
    Write-Host "No listener on port $p"
  }
}
