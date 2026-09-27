param (
    [int]$Drivers = 50
)

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "   Starting Fleet Simulation (Drivers: $Drivers)" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# Check if Backend is up on port 8000
$backendUrl = "http://localhost:8000/docs"
try {
    $resp = Invoke-WebRequest -Uri $backendUrl -Method Head -ErrorAction Stop
    Write-Host "Backend is Online." -ForegroundColor Green
}
catch {
    Write-Warning "Backend might be unreachable ($backendUrl). Ensure your container stack is running."
    Write-Warning "Attempting to start anyway..."
}

# Ensure DRIVER_PASSWORD is set for authentication
if (-not $env:DRIVER_PASSWORD) {
    $env:DRIVER_PASSWORD = "testpassword123"
    Write-Host "Assigned default DRIVER_PASSWORD environment variable." -ForegroundColor Yellow
}

# Run Simulator
Write-Host "Traffic generation active. Press Ctrl+C to stop." -ForegroundColor Yellow
python tools/simulators/fleet_sim.py --drivers $Drivers