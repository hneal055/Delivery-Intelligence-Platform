<#
.SYNOPSIS
    Warn on screen if the last successful backup is too old.

.DESCRIPTION
    Reads <BackupRoot>\last-success.txt (written by backup.ps1). If it is
    missing or older than -MaxAgeHours (default 26), shows a pop-up and
    exits 1. Run by the "DIP Backup Check" scheduled task at logon and
    every morning.
#>
param(
    [string]$BackupRoot = "C:\DIP-Backups",
    [int]$MaxAgeHours = 26,
    [switch]$Quiet
)

$marker = Join-Path $BackupRoot "last-success.txt"
$problem = $null
if (-not (Test-Path $marker)) {
    $problem = "No successful DIP backup has been recorded yet."
} else {
    $last = [datetime]::Parse((Get-Content $marker -Raw).Trim())
    $age = (Get-Date) - $last
    if ($age.TotalHours -gt $MaxAgeHours) {
        $problem = "The last successful DIP backup was {0:N0} hours ago ({1:g})." -f $age.TotalHours, $last
    }
}

if (-not $problem) {
    if (-not $Quiet) { Write-Host "Backups OK (last success $last)" -ForegroundColor Green }
    exit 0
}

$message = "$problem`n`nCheck that Docker Desktop is running, then run:`n  .\scripts\ops\backup.ps1`nSee $BackupRoot\backup.log for details."
Write-Host $message -ForegroundColor Red
# 48 = warning icon; waits up to 1 hour for the user to see it
(New-Object -ComObject WScript.Shell).Popup($message, 3600, "DIP backup warning", 48) | Out-Null
exit 1
