$ErrorActionPreference = "Stop"

& "$PSScriptRoot\load_env.ps1"

if (-not $env:INITIAL_ADMIN_PASSWORD) {
    Write-Error "INITIAL_ADMIN_PASSWORD is missing."
    exit 1
}

if (-not $env:INITIAL_DRIVER_PASSWORD) {
    Write-Error "INITIAL_DRIVER_PASSWORD is missing."
    exit 1
}

Write-Host "Initializing backend database..."
python "$PSScriptRoot\src\backend\init_db.py"
