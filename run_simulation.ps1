param (
    [int]$Drivers = 20
)

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   Starting Fleet Simulation (Drivers: $Drivers)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# Check if Backend is up
$backendUrl = "http://localhost:8000/docs"
try {
    $resp = Invoke-WebRequest -Uri $backendUrl -Method Head -ErrorAction Stop
    Write-Host "Backend is Online." -ForegroundColor Green
} catch {
    Write-Warning "Backend might be unreachable ($backendUrl). Ensure you ran .\start_platform.ps1"
    Write-Warning "Attempting to start anyway..."
}

# Run Simulator
Write-Host "Traffic generation active. Press Ctrl+C to stop." -ForegroundColor Yellow
python tools/simulators/fleet_sim.py --drivers $Drivers
