<#
.SYNOPSIS
    Prove the newest backup can be restored, and time it.

.DESCRIPTION
    Restores the newest dump in <BackupRoot>\db\daily into a scratch database
    (delivery_restore_test) next to the live one, compares row counts of the
    business tables with the live database, prints how long the restore took,
    and drops the scratch database. The live "delivery" database is never
    touched. Exit 1 if the restore fails or counts differ.

.EXAMPLE
    .\scripts\ops\test-restore.ps1
#>
param(
    [string]$BackupRoot = "C:\DIP-Backups",
    [string]$Dump = ""
)

$ErrorActionPreference = "Stop"
$DbContainer = "delivery_db"
$Scratch = "delivery_restore_test"
$Tables = @("users", "drivers", "packages", "dispatch_jobs", "delivery_proofs", "device_tokens")

if (-not $Dump) {
    $newest = Get-ChildItem (Join-Path $BackupRoot "db\daily") -Filter "dip-db-*.dump" |
        Sort-Object Name -Descending | Select-Object -First 1
    if (-not $newest) { Write-Host "No dumps in $BackupRoot\db\daily" -ForegroundColor Red; exit 1 }
    $Dump = $newest.FullName
}
Write-Host "Restoring $Dump into scratch database $Scratch ..."

function Psql($db, $sql) {
    (docker exec $DbContainer psql -U postgres -d $db -Atc $sql) -join ""
}

docker exec $DbContainer dropdb -U postgres --if-exists $Scratch | Out-Null
docker exec $DbContainer createdb -U postgres $Scratch
docker cp $Dump "${DbContainer}:/tmp/restore-test.dump" | Out-Null

$timer = [Diagnostics.Stopwatch]::StartNew()
# --no-owner: restore as postgres; errors such as "extension already exists" are reported, not fatal
docker exec $DbContainer pg_restore -U postgres -d $Scratch --no-owner /tmp/restore-test.dump 2>&1 |
    Where-Object { $_ -match "error" -and $_ -notmatch "already exists" } |
    ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
$timer.Stop()

$ok = $true
foreach ($t in $Tables) {
    $live = Psql "delivery" "select count(*) from $t"
    $restored = Psql $Scratch "select count(*) from $t"
    $mark = if ($live -eq $restored) { "ok" } else { $ok = $false; "DIFFERENT" }
    Write-Host ("  {0,-16} live {1,6}   restored {2,6}   {3}" -f $t, $live, $restored, $mark)
}

docker exec $DbContainer dropdb -U postgres $Scratch | Out-Null
docker exec $DbContainer rm -f /tmp/restore-test.dump | Out-Null

Write-Host ("Restore took {0:N1} s" -f $timer.Elapsed.TotalSeconds)
if ($ok) {
    Write-Host "Restore test PASSED (counts can differ only if data changed since the backup)" -ForegroundColor Green
    exit 0
}
Write-Host "Restore test: counts differ. If nothing changed since the backup, investigate." -ForegroundColor Yellow
exit 1
