param([switch]$KillOnly)

$port = 8000
$scriptDir = Split-Path $MyInvocation.MyCommand.Path -Parent

# 查找占用端口的进程
$pid = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING" |
  ForEach-Object { $_ -split '\s+' | Select-Object -Last 1 } |
  Select-Object -First 1

if ($pid) {
  Write-Host "[KILL] 杀掉 PID $pid (端口 $port)..." -ForegroundColor Yellow
  Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
  Start-Sleep 1
} else {
  Write-Host "[OK] 端口 $port 未被占用" -ForegroundColor Green
}

if (-not $KillOnly) {
  Set-Location "$scriptDir\backend"
  Write-Host "[START] 启动 uvicorn (DEV=1, --reload)" -ForegroundColor Cyan
  Write-Host "[HINT] Ctrl+C 停止`n" -ForegroundColor Gray
  $env:DEV = "1"
  python -m uvicorn main:app --host 0.0.0.0 --port $port --reload
}