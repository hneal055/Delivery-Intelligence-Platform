Write-Host ">>> Starting Delivery Intelligence Platform Environment..." -ForegroundColor Cyan

# 1. Check & Launch Emulator with fixed on-screen coordinates
$device = adb devices | Select-String "emulator"
if (-not $device) {
    Write-Host ">>> Launching Pixel 8 Emulator at fixed position (100, 100)..." -ForegroundColor Yellow
    Start-Process -FilePath "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" `
                  -ArgumentList "-avd Pixel_8 -no-snapshot -window-pos 100,100"
    Write-Host ">>> Waiting for Android device to boot..." -ForegroundColor Yellow
    adb wait-for-device
    Start-Sleep -Seconds 10
} else {
    Write-Host ">>> Pixel 8 Emulator is already running." -ForegroundColor Green
}

# 2. Automatically map reverse ports for Metro and Backend
Write-Host ">>> Configuring ADB Port Forwarding..." -ForegroundColor Cyan
adb reverse tcp:8081 tcp:8081
adb reverse tcp:8082 tcp:8082
adb reverse tcp:8000 tcp:8000
Write-Host ">>> Ports 8081, 8082, 8000 bridged successfully." -ForegroundColor Green

# 3. Launch Backend in a Dedicated Terminal Window
Write-Host ">>> Spawning Backend API (Uvicorn)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd C:\Projects\DELIVERYINTELLIGENCEPLATFORM; .\.venv\Scripts\Activate.ps1; cd src\backend; uvicorn main:app --reload --host 0.0.0.0 --port 8000"

# 4. Launch Metro Bundler in current terminal
Write-Host ">>> Starting Expo/Metro Bundler..." -ForegroundColor Cyan
cd C:\Projects\DELIVERYINTELLIGENCEPLATFORM\src\mobile
npx expo start -c
