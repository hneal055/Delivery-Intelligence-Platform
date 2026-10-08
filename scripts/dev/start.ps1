<#
.SYNOPSIS
    Start the Delivery Intelligence Platform for local development.

.DESCRIPTION
    Starts the Docker stack (Postgres/PostGIS, Redis, backend, telemetry worker,
    dashboard), waits for the database, applies migrations, seeds development
    accounts, and checks backend health. Data is kept between runs unless you
    pass -Reset.

    First-time setup: run .\scripts\dev\setup_secrets.ps1 to create .env.backend
    with the development account passwords.

.PARAMETER Reset
    Delete all containers AND volumes (database, Redis, uploads) before starting.
    Asks for confirmation.

.PARAMETER Simulate
    Start the fleet simulator in a separate window.

.PARAMETER Drivers
    Number of drivers to seed and simulate. Default 50.

.PARAMETER Monitoring
    Also start Prometheus, Alertmanager and Grafana
    (deploy/monitoring/docker-compose.monitoring.yml).
    Requires GF_SECURITY_ADMIN_PASSWORD in .env or .env.backend.

.PARAMETER Mobile
    Start the Android emulator, bridge ports with adb, and open the Expo bundler.

.PARAMETER Avd
    Android Virtual Device name used with -Mobile. Default Pixel_8.

.EXAMPLE
    .\scripts\dev\start.ps1
    .\scripts\dev\start.ps1 -Simulate -Drivers 10
    .\scripts\dev\start.ps1 -Reset
#>
param(
    [switch]$Reset,
    [switch]$Simulate,
    [int]$Drivers = 50,
    [switch]$Monitoring,
    [switch]$Mobile,
    [string]$Avd = "Pixel_8"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

function Step($text) { Write-Host "`n>>> $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host "ERROR: $text" -ForegroundColor Red; exit 1 }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Delivery Intelligence Platform - Start " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# --- Preflight -------------------------------------------------------------
Step "Checking Docker"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Fail "Docker was not found. Install Docker Desktop and try again."
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { Fail "Docker Desktop is not running. Start it and try again." }

# --- Development secrets ---------------------------------------------------
# Loaded into this process so compose interpolation, seeding and the
# simulator can read them. Never committed (see .gitignore).
$envFile = Join-Path $RepoRoot ".env.backend"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $name, $value = $line -split "=", 2
            [Environment]::SetEnvironmentVariable($name.Trim(), $value.Trim(), "Process")
        }
    }
    Write-Host "Loaded .env.backend" -ForegroundColor Green
} else {
    Write-Host "No .env.backend found; development accounts will not be seeded." -ForegroundColor Yellow
    Write-Host "Run .\scripts\dev\setup_secrets.ps1 to create it." -ForegroundColor Yellow
}

$composeFiles = @("-f", "docker-compose.yml")
if ($Monitoring) { $composeFiles += @("-f", "deploy/monitoring/docker-compose.monitoring.yml") }

# --- Optional reset --------------------------------------------------------
if ($Reset) {
    Write-Host "`n-Reset deletes the local database, Redis data and uploaded proofs." -ForegroundColor Yellow
    $answer = Read-Host "Type RESET to continue"
    if ($answer -ne "RESET") { Fail "Cancelled." }
    Step "Removing containers and volumes"
    docker compose @composeFiles down --volumes --remove-orphans
}

# --- Containers ------------------------------------------------------------
Step "Validating compose configuration"
docker compose @composeFiles config --quiet
if ($LASTEXITCODE -ne 0) { Fail "Docker Compose configuration is invalid." }

Step "Starting containers"
docker compose @composeFiles up -d --build
if ($LASTEXITCODE -ne 0) { Fail "One or more containers failed to start." }

Step "Waiting for the database"
$healthy = $false
for ($i = 0; $i -lt 30 -and -not $healthy; $i++) {
    $healthy = (docker inspect --format "{{.State.Health.Status}}" delivery_db 2>$null) -eq "healthy"
    if (-not $healthy) { Start-Sleep -Seconds 2 }
}
if (-not $healthy) { Fail "Database did not become healthy within 60s. Check: docker compose logs delivery_db" }
Write-Host "Database is healthy." -ForegroundColor Green

Step "Applying database migrations"
docker compose exec -T backend alembic upgrade head
if ($LASTEXITCODE -ne 0) { Fail "Migrations failed. Check: docker compose logs backend" }

# asyncpg caches prepared statements; restart so it sees schema changes.
docker compose restart backend | Out-Null

if ($env:INITIAL_ADMIN_PASSWORD -and $env:INITIAL_DRIVER_PASSWORD) {
    Step "Seeding development accounts and $Drivers drivers"
    $seedEnv = @(
        "-e", "INITIAL_ADMIN_PASSWORD=$env:INITIAL_ADMIN_PASSWORD",
        "-e", "INITIAL_DRIVER_PASSWORD=$env:INITIAL_DRIVER_PASSWORD"
    )
    if ($env:INITIAL_DISPATCHER_PASSWORD) {
        $seedEnv += @("-e", "INITIAL_DISPATCHER_PASSWORD=$env:INITIAL_DISPATCHER_PASSWORD")
    }
    docker compose exec -T @seedEnv backend python -m tools.seed_dev_data --drivers $Drivers
    if ($LASTEXITCODE -ne 0) { Fail "Seeding failed." }
}

# --- Health check ----------------------------------------------------------
Step "Checking backend health"
$backendUp = $false
for ($i = 0; $i -lt 15 -and -not $backendUp; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 3
        $backendUp = $true
        Write-Host "Backend health: $($health.status)" -ForegroundColor Green
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $backendUp) { Fail "Backend is not responding on http://localhost:8000/health. Check: docker compose logs backend" }

docker compose @composeFiles ps

# --- Optional extras -------------------------------------------------------
if ($Simulate) {
    $env:DRIVER_PASSWORD = if ($env:SIMULATOR_DRIVER_PASSWORD) { $env:SIMULATOR_DRIVER_PASSWORD } else { $env:INITIAL_DRIVER_PASSWORD }
    if (-not $env:DRIVER_PASSWORD) {
        Write-Host "Skipping simulator: no driver password in .env.backend." -ForegroundColor Yellow
    } else {
        Step "Starting fleet simulator ($Drivers drivers) in a new window"
        $python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
        if (-not (Test-Path $python)) { $python = "python" }
        Start-Process powershell -WorkingDirectory $RepoRoot -ArgumentList "-NoExit", "-Command",
            "& '$python' -m tools.simulators.fleet_sim --drivers $Drivers"
    }
}

if ($Mobile) {
    Step "Starting Android emulator and Expo"
    if (-not (Get-Command adb -ErrorAction SilentlyContinue)) { Fail "adb was not found. Install the Android SDK platform tools." }
    if (-not (adb devices | Select-String "emulator")) {
        Start-Process -FilePath "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" `
            -ArgumentList "-avd $Avd -no-snapshot -window-pos 100,100"
        adb wait-for-device
        Start-Sleep -Seconds 10
    }
    foreach ($port in 8081, 8082, 8000) { adb reverse "tcp:$port" "tcp:$port" | Out-Null }
    Write-Host "Bridged ports 8081, 8082, 8000 to the emulator." -ForegroundColor Green
    Start-Process powershell -WorkingDirectory (Join-Path $RepoRoot "src\mobile") -ArgumentList "-NoExit", "-Command", "npx expo start -c"
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host " Platform is running" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host " Backend API docs : http://localhost:8000/docs"
Write-Host " Dashboard        : http://localhost:5173"
if ($Monitoring) {
    Write-Host " Prometheus       : http://localhost:9090"
    Write-Host " Grafana          : http://localhost:3001 (admin / GF_SECURITY_ADMIN_PASSWORD)"
}
Write-Host " Logs             : docker compose logs -f"
Write-Host " Stop             : .\scripts\dev\stop.ps1"
