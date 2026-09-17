# =====================================================================
# Delivery Intelligence Platform - Clean Environment Startup Script
# =====================================================================

Write-Host " [1/4] Tearing down Docker containers and volumes..." -ForegroundColor Cyan
docker compose down --volumes --remove-orphans

# Stop any rogue Docker instances if present
$runningContainers = docker ps -a -q
if ($runningContainers) {
    Write-Host " [2/4] Forcibly stopping remaining containers..." -ForegroundColor Cyan
    docker stop $runningContainers 2>&1 | Out-Null
    docker rm $runningContainers 2>&1 | Out-Null
}

Write-Host " [3/4] Terminating stray local development processes..." -ForegroundColor Cyan
Stop-Process -Name "node", "vite", "python", "uvicorn" -Force -ErrorAction SilentlyContinue

Write-Host " [4/4] Freeing up critical development ports..." -ForegroundColor Cyan
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 80, 8000, 8002, 5173, 3500, 5432 } | ForEach-Object {
    $process = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
    if ($process) {
        Write-Host "   -> Stopping $($process.Name) (PID: $($process.Id)) on port $($_.LocalPort)" -ForegroundColor Yellow
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "`nEnvironment is fully scrubbed and ready for a fresh build!" -ForegroundColor Green