# Auto-detect local IP and update .env file for mobile development

$ErrorActionPreference = "Stop"

Write-Host "`n=== Mobile App Environment Setup ===" -ForegroundColor Cyan

# Get primary Wi-Fi/Ethernet adapter IP
$localIP = Get-NetIPAddress -AddressFamily IPv4 | 
    Where-Object { $_.InterfaceAlias -match 'Wi-Fi|Ethernet' -and $_.IPAddress -notmatch '^169\.254' } |
    Select-Object -First 1 -ExpandProperty IPAddress

if (-not $localIP) {
    Write-Warning "Could not auto-detect local IP. Please set manually in src/mobile/.env"
    exit 1
}

Write-Host "`nDetected Local IP: " -NoNewline
Write-Host $localIP -ForegroundColor Green

$envPath = Join-Path $PSScriptRoot "src\mobile\.env"

if (Test-Path $envPath) {
    $choice = Read-Host "`n.env file exists. Update with detected IP? (y/n)"
    if ($choice -ne 'y') {
        Write-Host "Skipping update." -ForegroundColor Yellow
        exit 0
    }
}

# Create or update .env file
@"
# Mobile App Environment Configuration (Auto-generated $(Get-Date -Format 'yyyy-MM-dd HH:mm'))

# Backend API Configuration
EXPO_PUBLIC_API_HOST=$localIP
EXPO_PUBLIC_API_PORT=8000
"@ | Set-Content -Path $envPath

Write-Host "`n✓ Updated $envPath" -ForegroundColor Green
Write-Host "`nBackend URL: " -NoNewline
Write-Host "http://$localIP:8000" -ForegroundColor Cyan

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Ensure your iPhone is on the same Wi-Fi network"
Write-Host "2. Start backend: .\start_platform.ps1"
Write-Host "3. Start mobile app: cd src\mobile; npm start"
