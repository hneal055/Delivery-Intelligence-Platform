$ErrorActionPreference = "Stop"

$envFile = Join-Path $PSScriptRoot ".env.backend"

if (-not (Test-Path $envFile)) {
    Write-Error ".env.backend was not found. Run .\setup_secrets.ps1 first."
    exit 1
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()

    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line -split "=", 2
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()

        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

Write-Host "Environment variables loaded from .env.backend"
