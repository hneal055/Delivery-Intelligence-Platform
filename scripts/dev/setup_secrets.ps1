$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$envFile = Join-Path $RepoRoot ".env.backend"

if (Test-Path $envFile) {
    $answer = Read-Host ".env.backend already exists. Replace it? Type YES to continue"
    if ($answer -ne "YES") {
        Write-Host "Cancelled."
        exit 0
    }
}

Write-Host ""
Write-Host "Enter a local development password for the admin account."
$adminPassword = Read-Host "Admin password" -AsSecureString
$adminPasswordPlain = [System.Net.NetworkCredential]::new("", $adminPassword).Password

Write-Host ""
Write-Host "Enter a local development password for simulator driver accounts."
$driverPassword = Read-Host "Driver password" -AsSecureString
$driverPasswordPlain = [System.Net.NetworkCredential]::new("", $driverPassword).Password

Write-Host ""
Write-Host "Enter a local development password for the dispatcher1 account (leave blank to skip)."
$dispatcherPassword = Read-Host "Dispatcher password" -AsSecureString
$dispatcherPasswordPlain = [System.Net.NetworkCredential]::new("", $dispatcherPassword).Password

@"
INITIAL_ADMIN_PASSWORD=$adminPasswordPlain
INITIAL_DRIVER_PASSWORD=$driverPasswordPlain
SIMULATOR_DRIVER_PASSWORD=$driverPasswordPlain
INITIAL_DISPATCHER_PASSWORD=$dispatcherPasswordPlain
"@ | Set-Content -Path $envFile -Encoding utf8

Write-Host ""
Write-Host "Created .env.backend"
Write-Host "This file must not be committed to Git."
