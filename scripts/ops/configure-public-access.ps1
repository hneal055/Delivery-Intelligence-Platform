<#
.SYNOPSIS
    Put DIP on the internet through a Cloudflare Tunnel (or take it off).

.DESCRIPTION
    Prerequisites (one-time, in your Cloudflare account; see the Operations
    Manual, section 10):
      - your domain is on Cloudflare (nameservers changed at the registrar)
      - a tunnel exists, with public hostname <Hostname> -> http://frontend:80
    This script then:
      1. asks for the tunnel token (not echoed, never printed)
      2. writes to .env: ENVIRONMENT=production, a DIAD_API_KEY if missing,
         BACKEND_CORS_ORIGINS=https://<Hostname>, COMPOSE_PROFILES=tunnel and
         CLOUDFLARE_TUNNEL_TOKEN
      3. points the phone app at https://<Hostname>/api (src/mobile/.env)
      4. restarts the stack and checks https://<Hostname>/api/health
    -Disable removes the tunnel and returns to office-Wi-Fi-only development
    mode (the phone app goes back to the office PC's address).

.EXAMPLE
    .\scripts\ops\configure-public-access.ps1 -Hostname dip.chicagocargocouriers.com
    .\scripts\ops\configure-public-access.ps1 -Disable
#>
param(
    [string]$Hostname = "",
    [switch]$Disable
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot
$envPath = Join-Path $RepoRoot ".env"
$mobileEnvPath = Join-Path $RepoRoot "src\mobile\.env"

function Set-EnvValues($path, [hashtable]$values, [string[]]$remove = @()) {
    $lines = if (Test-Path $path) { @(Get-Content $path) } else { @() }
    $keys = @($values.Keys) + $remove
    $kept = $lines | Where-Object {
        $name = ($_ -split "=", 2)[0].Trim()
        -not ($keys -contains $name)
    }
    $new = @($kept) + ($values.GetEnumerator() | Sort-Object Name | ForEach-Object { "$($_.Name)=$($_.Value)" })
    Set-Content -Path $path -Value $new -Encoding utf8
}

function Get-EnvValue($path, $name) {
    if (-not (Test-Path $path)) { return "" }
    $line = Get-Content $path | Where-Object { ($_ -split "=", 2)[0].Trim() -eq $name } | Select-Object -Last 1
    if ($line) { return ($line -split "=", 2)[1].Trim() }
    return ""
}

if ($Disable) {
    Set-EnvValues $envPath @{ ENVIRONMENT = "development" } @("COMPOSE_PROFILES", "CLOUDFLARE_TUNNEL_TOKEN", "BACKEND_CORS_ORIGINS")
    Set-EnvValues $mobileEnvPath @{} @("EXPO_PUBLIC_API_URL")
    docker compose --profile tunnel stop cloudflared 2>$null | Out-Null
    docker compose --profile tunnel rm -f cloudflared 2>$null | Out-Null
    docker compose up -d
    Write-Host "Public access is OFF. DIP is reachable on the office network only." -ForegroundColor Yellow
    exit 0
}

if (-not $Hostname -or $Hostname -notmatch "^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$") {
    Write-Host "Give the public hostname, e.g. -Hostname dip.yourdomain.com" -ForegroundColor Red
    exit 2
}

$secure = Read-Host "Paste the Cloudflare tunnel token, or the whole 'docker run ...' command (it will not be shown)" -AsSecureString
$token = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
# Cloudflare's copy button copies the full docker command; keep only the token
if ($token -match "--token\s+(\S+)") { $token = $Matches[1] }
$token = $token.Trim().Trim('"', "'")
if ($token.Length -lt 50 -or $token -match "\s") {
    Write-Host "That does not look like a tunnel token (they are long). Nothing was changed." -ForegroundColor Red
    exit 1
}

$values = @{
    ENVIRONMENT = "production"
    BACKEND_CORS_ORIGINS = "https://$Hostname"
    COMPOSE_PROFILES = "tunnel"
    CLOUDFLARE_TUNNEL_TOKEN = $token
}
if (-not (Get-EnvValue $envPath "DIAD_API_KEY")) {
    $bytes = New-Object byte[] 32
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $values["DIAD_API_KEY"] = -join ($bytes | ForEach-Object { $_.ToString("x2") })
    Write-Host "Generated a device key (DIAD_API_KEY) in .env"
}
Set-EnvValues $envPath $values
Set-EnvValues $mobileEnvPath @{ EXPO_PUBLIC_API_URL = "https://$Hostname/api" }
Write-Host "Updated .env and src\mobile\.env (secrets not shown)" -ForegroundColor Green

docker compose up -d
if ($LASTEXITCODE -ne 0) { Write-Host "docker compose failed; see the output above." -ForegroundColor Red; exit 1 }

Write-Host "Waiting for the tunnel and backend..."
$ok = $false
for ($i = 0; $i -lt 18; $i++) {
    Start-Sleep -Seconds 5
    try {
        $r = Invoke-RestMethod -Uri "https://$Hostname/api/health" -TimeoutSec 5
        if ($r.status -eq "ok") { $ok = $true; break }
    } catch { }
}
if ($ok) {
    Write-Host "Public access is ON: https://$Hostname (dashboard) and https://$Hostname/api (phones)." -ForegroundColor Green
    Write-Host "Restart 'npm run go' in src\mobile so the app uses the new address."
    exit 0
}
$tunnelUp = (docker inspect -f "{{.State.Running}}" delivery_tunnel 2>$null) -eq "true"
if ($tunnelUp) {
    Write-Host "The tunnel connector is running, but https://$Hostname/api/health did not answer yet." -ForegroundColor Yellow
    Write-Host "If Cloudflare is still waiting: click Continue there and add the public hostname"
    Write-Host "($Hostname -> HTTP frontend:80). If the domain is still Pending, wait until it is Active."
    Write-Host "Then just open https://$Hostname. No need to rerun this script."
} else {
    Write-Host "The tunnel connector is not running. Check: docker compose logs cloudflared --tail 30" -ForegroundColor Red
}
exit 1
