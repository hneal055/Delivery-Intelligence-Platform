<#
.SYNOPSIS
    Copy new proof-of-delivery photos to the backup folders (runs hourly).

.DESCRIPTION
    The nightly backup copies photos once a day; this closes the gap so a
    photo taken in the afternoon is not lost if the disk fails before 23:00.
    Copies only new or changed files (additive; never deletes) to
    BackupRoot\proofs and, if given, OffsiteDir\proofs. Takes seconds.
    Logs to photos.log in the backup folder only when photos were copied
    or something failed. Exits 1 on failure so Task Scheduler records it.

.EXAMPLE
    .\scripts\ops\backup-photos.ps1 -OffsiteDir "$env:OneDrive\DIP-Backups"
#>
param(
    [string]$BackupRoot = "C:\DIP-Backups",
    [string]$OffsiteDir = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$photoSource = Join-Path $RepoRoot "src\uploads\proofs"
$proofsDir = Join-Path $BackupRoot "proofs"
$logFile = Join-Path $BackupRoot "photos.log"
New-Item -ItemType Directory -Force $proofsDir | Out-Null

function Log($text) {
    $line = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $text
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

if (-not (Test-Path $photoSource)) {
    Write-Host "No proof photo folder ($photoSource); nothing to copy"
    exit 0
}

# robocopy exit codes: 0 nothing copied, 1-7 copied/extra files, 8+ failure
function CopyNew($from, $to, $label) {
    robocopy $from $to /E /XO /R:2 /W:5 /NFL /NDL /NJH /NJS /NP | Out-Null
    $code = $LASTEXITCODE
    if ($code -ge 8) {
        Log "FAILED: copying photos to $label (robocopy $code)"
        exit 1
    }
    return ($code -band 1) -eq 1
}

$copied = CopyNew $photoSource $proofsDir "this PC"
if ($OffsiteDir) {
    $offsiteCopied = CopyNew $proofsDir (Join-Path $OffsiteDir "proofs") "$OffsiteDir"
    $copied = $copied -or $offsiteCopied
}
if ($copied) {
    Log ("New photos copied" + $(if ($OffsiteDir) { " (this PC and $OffsiteDir)" } else { " (this PC only)" }))
}
exit 0
