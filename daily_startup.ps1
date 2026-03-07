~~~~`<#
.SYNOPSIS
Daily startup script for Delivery Intelligence Platform.
Automates the process of pulling updates, starting backend services,
launching the frontend, and verifying the environment.
#>

$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Get-Location).Path
}
Set-Location $RepoRoot

function Write-Section {
    param([string]$Message)
    Write-Host "`n===================================================" -ForegroundColor Cyan
    Write-Host "   $Message" -ForegroundColor Cyan
    Write-Host "===================================================" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host "`n-> $Message" -ForegroundColor Yellow
}

Write-Section "Delivery Intelligence Platform - Daily Routine"

# 1. Git Pull
Write-Step "Checking for code updates..."
try {
    $status = git status --porcelain
    if ($status) {
        Write-Warning "You have uncommitted changes. Skipping 'git pull' to avoid conflicts."
    }
    else {
        Write-Host "Pulling latest changes from origin..." -ForegroundColor Gray
        git pull
    }
}
catch {
    Write-Warning "Git operation failed. Use with caution."
}

# 2. Start Backend & Infrastructure
Write-Step "Initializing Backend Infrastructure..."
if (Test-Path ".\start_platform.ps1") {
    # We call the existing start_platform script
    # It handles Docker, Migrations, Seeding, Grafana, and Simulation
    try {
        .\start_platform.ps1
    }
    catch {
        Write-Error "Failed to execute start_platform.ps1"
        exit 1
    }
}
else {
    Write-Error "start_platform.ps1 not found in current directory."
    exit 1
}

# 3. Open Monitoring Dashboards
Write-Step "Opening Monitoring Dashboards..."
Write-Host "Launching Grafana  : http://localhost:3500" -ForegroundColor Gray
Start-Process "http://localhost:3500"
Write-Host "Launching Prometheus: http://localhost:9090" -ForegroundColor Gray
Start-Process "http://localhost:9090"

# 4. Start Frontend
Write-Step "Launching Frontend (Vite)..."
$frontendPath = Join-Path $RepoRoot "src\web"
if (Test-Path $frontendPath) {
    Push-Location $frontendPath
    
    if (Test-Path "package.json") {
        Write-Host "Checking frontend dependencies..." -ForegroundColor Gray
        try {
            # Quiet install to avoid spamming unless error
            npm install --silent
        }
        catch {
            Write-Warning "npm install had issues. Continuing to start..."
        }

        Write-Host "Starting Vite Development Server in new window..." -ForegroundColor Green
        $absPath = (Resolve-Path $frontendPath).Path
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev" -WorkingDirectory $absPath -WindowStyle Normal
    }
    else {
        Write-Warning "No package.json found in $frontendPath"
    }
    Pop-Location
}
else {
    Write-Warning "Frontend path $frontendPath not found."
}

# 5. Start Mobile App (Expo)
Write-Step "Launching Mobile App (Expo)..."
$mobilePath = Join-Path $RepoRoot "src\mobile"
if (Test-Path $mobilePath) {
    Push-Location $mobilePath

    if (Test-Path "package.json") {
        Write-Host "Checking mobile dependencies..." -ForegroundColor Gray
        try {
            npm install --silent
        }
        catch {
            Write-Warning "npm install had issues. Continuing to start..."
        }

        Write-Host "Starting Expo Development Server in new window..." -ForegroundColor Green
        $absPath = (Resolve-Path $mobilePath).Path
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm start" -WorkingDirectory $absPath -WindowStyle Normal
    }
    else {
        Write-Warning "No package.json found in $mobilePath"
    }
    Pop-Location
}
else {
    Write-Warning "Mobile path $mobilePath not found."
}

Write-Section "Daily Startup Complete"
Write-Host "1. Backend API        : http://localhost:8002/docs"
Write-Host "2. Grafana            : http://localhost:3500  (admin / new_bizness123)"
Write-Host "3. Prometheus         : http://localhost:9090"
Write-Host "4. Simulation         : Running in separate window"
Write-Host "5. Frontend           : Running in separate window (http://localhost:5173)"
Write-Host "6. Mobile (Expo)      : Running in separate window (scan QR for device)"
Write-Host "`nHappy Coding!" -ForegroundColor Green


