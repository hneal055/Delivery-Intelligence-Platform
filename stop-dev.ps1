# C:\Projects\DELIVERYINTELLIGENCEPLATFORM\stop-dev.ps1

Write-Host ">>> Teardown: Shutting down Delivery Intelligence Platform..." -ForegroundColor Cyan

# 1. Gracefully shut down the Android Emulator
$device = adb devices 2>$null | Select-String "emulator"
if ($device) {
    Write-Host ">>> Stopping Android Emulator..." -ForegroundColor Yellow
    adb emu kill 2>$null
    Start-Sleep -Seconds 2
    Write-Host ">>> Emulator powered down." -ForegroundColor Green
}
else {
    Write-Host ">>> No active Android emulator detected." -ForegroundColor DarkGray
}

# 2. Clear ADB Port Forwarding / Reverse Rules
Write-Host ">>> Clearing ADB port forwardings..." -ForegroundColor Yellow
adb reverse --remove-all 2>$null
Write-Host ">>> ADB port bridges cleared." -ForegroundColor Green

# 3. Terminate Backend API Server (Uvicorn / Python processes on port 8000)
Write-Host ">>> Stopping Backend API (port 8000)..." -ForegroundColor Yellow
$backendPort = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
if ($backendPort) {
    $backendPids = $backendPort.OwningProcess | Where-Object { $_ -gt 4 } | Select-Object -Unique
    foreach ($targetPid in $backendPids) {
        try {
            Stop-Process -Id $targetPid -Force -ErrorAction Stop
        }
        catch {
            Write-Host "    Could not terminate PID $targetPid (may require admin privileges)." -ForegroundColor DarkGray
        }
    }
    Write-Host ">>> Backend API stopped." -ForegroundColor Green
}
else {
    Write-Host ">>> No process running on port 8000." -ForegroundColor DarkGray
}

# 4. Terminate Metro / Expo Bundler (Node.js processes on ports 8081 & 8082)
Write-Host ">>> Stopping Metro Bundler (ports 8081/8082)..." -ForegroundColor Yellow
$metroPorts = Get-NetTCPConnection -LocalPort 8081, 8082 -ErrorAction SilentlyContinue
if ($metroPorts) {
    $metroPids = $metroPorts.OwningProcess | Where-Object { $_ -gt 4 } | Select-Object -Unique
    foreach ($targetPid in $metroPids) {
        try {
            Stop-Process -Id $targetPid -Force -ErrorAction Stop
        }
        catch {
            Write-Host "    Could not terminate PID $targetPid (may require admin privileges)." -ForegroundColor DarkGray
        }
    }
    Write-Host ">>> Metro bundler stopped." -ForegroundColor Green
}
else {
    Write-Host ">>> No process running on Metro ports." -ForegroundColor DarkGray
}

Write-Host "`n>>> All services cleanly terminated. Ready for next session." -ForegroundColor Cyan