$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Delivery Intelligence Platform Startup " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Confirm this script is being run from the repository root.
$repoRoot = git rev-parse --show-toplevel 2>$null

if (-not $repoRoot) {
    Write-Error "This folder is not a Git repository."
    exit 1
}

Set-Location $repoRoot
Write-Host "Repository root: $repoRoot" -ForegroundColor Green

# Check Docker.
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker was not found. Start Docker Desktop and try again."
    exit 1
}

try {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is not running."
    }
}
catch {
    Write-Error "Docker Desktop is not running. Start it and try again."
    exit 1
}

# Check Docker Compose file.
if (-not (Test-Path "docker-compose.yml")) {
    Write-Error "docker-compose.yml was not found in $repoRoot."
    exit 1
}

# Select the environment file if it exists.
$composeArgs = @()

if (Test-Path ".env.backend") {
    Write-Host "Using .env.backend for Compose variables." -ForegroundColor Green
    $composeArgs += @("--env-file", ".env.backend")
}
else {
    Write-Host "No .env.backend file found. Continuing without it." -ForegroundColor Yellow
}

# Validate the Compose configuration.
Write-Host ""
Write-Host "Validating Docker Compose configuration..." -ForegroundColor Cyan

docker compose @composeArgs config --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker Compose configuration is invalid."
    exit 1
}

# Start or rebuild the application.
Write-Host ""
Write-Host "Starting application containers..." -ForegroundColor Cyan

docker compose @composeArgs up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Error "One or more containers failed to start."
    exit 1
}

# Display service status.
Write-Host ""
Write-Host "Container status:" -ForegroundColor Cyan
docker compose @composeArgs ps

Write-Host ""
Write-Host "Recent container logs:" -ForegroundColor Cyan
docker compose @composeArgs logs --tail=40

Write-Host ""
Write-Host "Startup complete." -ForegroundColor Green
Write-Host "To stop the platform, run: docker compose down" -ForegroundColor Yellow
Write-Host "To view live logs, run: docker compose logs -f" -ForegroundColor Yellow
