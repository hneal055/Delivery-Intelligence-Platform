<#
.SYNOPSIS
    Stop the Delivery Intelligence Platform local development environment.

.DESCRIPTION
    Stops the Docker stack (data is kept), the Expo/Metro bundler, and the
    Android emulator if one is running. Only processes on this project's
    Metro ports are stopped; other Python/Node processes are left alone.

.PARAMETER Wipe
    Also delete the Docker volumes (database, Redis, uploads). Asks for confirmation.

.PARAMETER Monitoring
    Also stop the monitoring stack started with start.ps1 -Monitoring.
#>
param(
    [switch]$Wipe,
    [switch]$Monitoring
)

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

Write-Host ">>> Stopping Delivery Intelligence Platform..." -ForegroundColor Cyan

# --- Docker stack ----------------------------------------------------------
$composeFiles = @("-f", "docker-compose.yml")
if ($Monitoring) {
    # The monitoring file requires this variable even when stopping.
    if (-not $env:GF_SECURITY_ADMIN_PASSWORD) { $env:GF_SECURITY_ADMIN_PASSWORD = "unused-on-stop" }
    $composeFiles += @("-f", "deploy/monitoring/docker-compose.monitoring.yml")
}

$downArgs = @("down", "--remove-orphans")
if ($Wipe) {
    Write-Host "-Wipe deletes the local database, Redis data and uploaded proofs." -ForegroundColor Yellow
    $answer = Read-Host "Type WIPE to continue"
    if ($answer -ne "WIPE") { Write-Host "Cancelled." -ForegroundColor Yellow; exit 1 }
    $downArgs += "--volumes"
}

if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker compose @composeFiles @downArgs
} else {
    Write-Host "Docker not found; skipping containers." -ForegroundColor DarkGray
}

# --- Expo / Metro bundler (ports 8081, 8082) -------------------------------
$metro = Get-NetTCPConnection -LocalPort 8081, 8082 -State Listen -ErrorAction SilentlyContinue
foreach ($procId in ($metro.OwningProcess | Where-Object { $_ -gt 4 } | Select-Object -Unique)) {
    try {
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Write-Host "Stopped Metro bundler (PID $procId)." -ForegroundColor Green
    } catch {
        Write-Host "Could not stop PID $procId (may need admin rights)." -ForegroundColor DarkGray
    }
}

# --- Android emulator ------------------------------------------------------
if (Get-Command adb -ErrorAction SilentlyContinue) {
    adb reverse --remove-all 2>$null
    if (adb devices 2>$null | Select-String "emulator") {
        adb emu kill 2>$null
        Write-Host "Stopped Android emulator." -ForegroundColor Green
    }
}

Write-Host ">>> Stopped." -ForegroundColor Cyan
