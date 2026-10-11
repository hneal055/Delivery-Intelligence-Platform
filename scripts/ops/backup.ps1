<#
.SYNOPSIS
    Back up the DIP database and proof-of-delivery photos.

.DESCRIPTION
    1. pg_dump of the "delivery" database (custom format), written inside the
       database container and copied out with docker cp (byte-safe).
    2. Checks the dump is readable (pg_restore --list) before keeping it.
    3. Keeps 7 daily and 4 weekly dumps (a weekly copy is taken on Sundays,
       or whenever the newest weekly copy is more than 7 days old).
    4. Copies new proof photos (additive; never deletes).
    5. Optionally mirrors everything to an off-machine folder (OneDrive, NAS,
       external drive) given with -OffsiteDir.
    Writes backup.log and last-success.txt in the backup folder. Exits 1 on
    any failure so Task Scheduler records it.

.PARAMETER BackupRoot
    Local backup folder. Default C:\DIP-Backups.

.PARAMETER OffsiteDir
    Optional folder that is NOT on this PC's disk (e.g. a OneDrive folder,
    \\nas\share\DIP, or an external drive). Leave empty to skip.

.EXAMPLE
    .\scripts\ops\backup.ps1
    .\scripts\ops\backup.ps1 -OffsiteDir "$env:OneDrive\DIP-Backups"
#>
param(
    [string]$BackupRoot = "C:\DIP-Backups",
    [string]$OffsiteDir = "",
    [int]$KeepDaily = 7,
    [int]$KeepWeekly = 4
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$DbContainer = "delivery_db"
$DbName = "delivery"

$dailyDir = Join-Path $BackupRoot "db\daily"
$weeklyDir = Join-Path $BackupRoot "db\weekly"
$proofsDir = Join-Path $BackupRoot "proofs"
$logFile = Join-Path $BackupRoot "backup.log"
New-Item -ItemType Directory -Force $dailyDir, $weeklyDir, $proofsDir | Out-Null

function Log($text) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $text
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

function Fail($text) {
    Log "FAILED: $text"
    exit 1
}

function Prune($dir, $keep) {
    Get-ChildItem $dir -Filter "dip-db-*.dump" | Sort-Object Name -Descending |
        Select-Object -Skip $keep | ForEach-Object {
            Remove-Item $_.FullName -Force
            Log "Pruned $($_.Name)"
        }
}

Log "=== Backup started ==="

# --- Database ---------------------------------------------------------------
$running = docker inspect -f "{{.State.Running}}" $DbContainer 2>$null
if ($running -ne "true") { Fail "Container $DbContainer is not running (is Docker Desktop up?)" }

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dumpName = "dip-db-$stamp.dump"
$dumpPath = Join-Path $dailyDir $dumpName

docker exec $DbContainer pg_dump -U postgres -Fc -f /tmp/dip-backup.dump $DbName
if ($LASTEXITCODE -ne 0) { Fail "pg_dump returned $LASTEXITCODE" }

$tables = (docker exec $DbContainer pg_restore --list /tmp/dip-backup.dump | Select-String "TABLE DATA").Count
if ($tables -lt 1) { Fail "Dump is not readable (no table data found)" }

docker cp "${DbContainer}:/tmp/dip-backup.dump" $dumpPath | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "docker cp returned $LASTEXITCODE" }
docker exec $DbContainer rm -f /tmp/dip-backup.dump | Out-Null

$size = (Get-Item $dumpPath).Length
if ($size -lt 1024) { Fail "Dump is suspiciously small ($size bytes)" }
Log ("Database dump {0}: {1:N0} KB, {2} tables with data" -f $dumpName, ($size / 1KB), $tables)

# Weekly copy on Sundays, or if the newest weekly copy is over 7 days old;
# at most one per day, so extra runs on a Sunday don't push out older weeks
$newestWeekly = Get-ChildItem $weeklyDir -Filter "dip-db-*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
$weeklyToday = $newestWeekly -and $newestWeekly.LastWriteTime.Date -eq (Get-Date).Date
$weeklyStale = -not $newestWeekly -or $newestWeekly.LastWriteTime -lt (Get-Date).AddDays(-7)
if (-not $weeklyToday -and ((Get-Date).DayOfWeek -eq "Sunday" -or $weeklyStale)) {
    Copy-Item $dumpPath (Join-Path $weeklyDir $dumpName)
    Log "Weekly copy kept"
}

Prune $dailyDir $KeepDaily
Prune $weeklyDir $KeepWeekly

# --- Proof photos ------------------------------------------------------------
$photoSource = Join-Path $RepoRoot "src\uploads\proofs"
if (Test-Path $photoSource) {
    # /E subfolders, /XO skip unchanged, no /MIR: a photo is never deleted from the backup
    robocopy $photoSource $proofsDir /E /XO /R:2 /W:5 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Fail "robocopy of proof photos returned $LASTEXITCODE" }
    Log "Proof photos copied"
} else {
    Log "No local proof photo folder ($photoSource); skipped"
}

# --- Off-machine copy ----------------------------------------------------------
if ($OffsiteDir) {
    New-Item -ItemType Directory -Force $OffsiteDir | Out-Null
    # Database dumps mirror the local retention; photos are additive
    robocopy (Join-Path $BackupRoot "db") (Join-Path $OffsiteDir "db") /MIR /R:2 /W:5 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Fail "Off-machine copy of dumps returned $LASTEXITCODE" }
    robocopy $proofsDir (Join-Path $OffsiteDir "proofs") /E /XO /R:2 /W:5 /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { Fail "Off-machine copy of photos returned $LASTEXITCODE" }
    Log "Copied off-machine to $OffsiteDir"
} else {
    Log "WARNING: no -OffsiteDir; backups are only on this PC"
}

Set-Content -Path (Join-Path $BackupRoot "last-success.txt") -Value (Get-Date -Format "o")
Log "=== Backup finished ==="
exit 0
