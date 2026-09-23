$ErrorActionPreference = "Stop"

& "$PSScriptRoot\load_env.ps1"

if (-not $env:SIMULATOR_DRIVER_PASSWORD) {
    Write-Error "SIMULATOR_DRIVER_PASSWORD is missing."
    exit 1
}

Write-Host "Starting fleet simulator..."
python "$PSScriptRoot\tools\simulators\fleet_sim.py"
