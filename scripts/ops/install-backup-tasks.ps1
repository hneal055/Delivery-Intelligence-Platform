<#
.SYNOPSIS
    Schedule the nightly DIP backup and the morning backup check.

.DESCRIPTION
    Registers two Windows scheduled tasks for the current user:
      "DIP Nightly Backup"  daily at -At (default 23:00); runs late if the PC
                            was off or asleep at that time
      "DIP Backup Check"    at logon and daily at 09:00; pops up a warning if
                            the last good backup is over 26 hours old
    Tasks run only while you are logged on, because Docker Desktop runs in
    your session. Re-run to change the time or the off-machine folder.

    Run from an elevated PowerShell ("Run as administrator"); Windows denies
    creating these tasks otherwise.

.EXAMPLE
    .\scripts\ops\install-backup-tasks.ps1 -OffsiteDir "$env:OneDrive\DIP-Backups"
    .\scripts\ops\install-backup-tasks.ps1 -Remove
#>
param(
    [string]$OffsiteDir = "",
    [string]$BackupRoot = "C:\DIP-Backups",
    [string]$At = "23:00",
    [switch]$Remove
)

$ErrorActionPreference = "Stop"
$backupTask = "DIP Nightly Backup"
$checkTask = "DIP Backup Check"

if ($Remove) {
    foreach ($t in @($backupTask, $checkTask)) {
        Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction SilentlyContinue
    }
    Write-Host "Removed the DIP backup tasks."
    exit 0
}

$shell = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $shell) { $shell = (Get-Command powershell).Source }
$opsDir = $PSScriptRoot
$user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$principal = New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$backupArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$opsDir\backup.ps1`" -BackupRoot `"$BackupRoot`""
if ($OffsiteDir) { $backupArgs += " -OffsiteDir `"$OffsiteDir`"" }
Register-ScheduledTask -TaskName $backupTask -Force -Principal $principal -Settings $settings `
    -Trigger (New-ScheduledTaskTrigger -Daily -At $At) `
    -Action (New-ScheduledTaskAction -Execute $shell -Argument $backupArgs -WorkingDirectory $opsDir) `
    -Description "Delivery Intelligence Platform: nightly database + proof photo backup" -ErrorAction Stop | Out-Null

$checkArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$opsDir\check-backup.ps1`" -BackupRoot `"$BackupRoot`" -Quiet"
Register-ScheduledTask -TaskName $checkTask -Force -Principal $principal -Settings $settings `
    -Trigger @((New-ScheduledTaskTrigger -AtLogOn -User $user), (New-ScheduledTaskTrigger -Daily -At "09:00")) `
    -Action (New-ScheduledTaskAction -Execute $shell -Argument $checkArgs -WorkingDirectory $opsDir) `
    -Description "Delivery Intelligence Platform: warn if the last backup is over 26 hours old" -ErrorAction Stop | Out-Null

# Confirm both tasks really exist before reporting success
foreach ($t in @($backupTask, $checkTask)) {
    if (-not (Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue)) {
        Write-Host "Task '$t' was not created. Run this script as administrator." -ForegroundColor Red
        exit 1
    }
}
Write-Host "Scheduled '$backupTask' daily at $At and '$checkTask' at logon and 09:00." -ForegroundColor Green
if ($OffsiteDir) {
    Write-Host "Off-machine copy: $OffsiteDir"
} else {
    Write-Host "WARNING: no -OffsiteDir. Backups stay on this PC only; re-run with -OffsiteDir to fix." -ForegroundColor Yellow
}
