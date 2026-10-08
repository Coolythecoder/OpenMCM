[CmdletBinding()]
param(
    [string] $SkyrimPath = 'E:\SteamLibrary\steamapps\common\Skyrim Special Edition',
    # Full dumps include private memory and can be several GB. Keep them local.
    [switch] $FullMemory,
    # Direct capture can pause the target while writing. Use only deliberately
    # when a clone snapshot is insufficient for a particular investigation.
    [switch] $NoClone,
    [ValidateRange(1, 600)][int] $CaptureTimeoutSeconds = 15
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
. (Join-Path $PSScriptRoot 'MinidumpValidation.ps1')
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$captureTool = Join-Path $projectRoot '.tools\procdump-20260906\bin\procdump64.exe'
$expectedHash = 'D1FC99AE304BD1D2BF28ABEB62531DA959E2431916194981B88C958FD713A8E6'
if ((Get-FileHash -LiteralPath $captureTool -Algorithm SHA256).Hash -ne $expectedHash) {
    throw 'ProcDump has changed since its Microsoft signature was verified.'
}
$signature = Get-AuthenticodeSignature -LiteralPath $captureTool
if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'O=Microsoft Corporation') {
    throw 'ProcDump does not have a valid Microsoft signature.'
}

$expectedGame = [IO.Path]::GetFullPath((Join-Path $SkyrimPath 'SkyrimSE.exe'))
$games = @(Get-Process -Name SkyrimSE -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and [IO.Path]::GetFullPath($_.Path) -eq $expectedGame
})
if ($games.Count -ne 1) {
    throw 'Exactly one SkyrimSE process from the configured game directory must be running.'
}

# Unique local output, no overwrite, upload, game-file changes, or permanent
# postmortem-debugger registration. Invoke only after the user reproduces the
# freeze, before Ctrl clears it. Clone snapshots reduce interruption of Skyrim.
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$captureRoot = Join-Path $projectRoot "build\diagnostics\skyrim-hang-$stamp"
New-Item -ItemType Directory -Path $captureRoot -ErrorAction Stop | Out-Null
$capturePid = $games[0].Id
$dumpType = if ($FullMemory) { '-ma' } else { '-mm' }
$captureArgs = @('-accepteula', $dumpType)
if (-not $NoClone) { $captureArgs += @('-r', '1', '-a') }
$captureArgs += @('-at', "$CaptureTimeoutSeconds", '-n', '2', '-s', '1', "$capturePid", $captureRoot)
if ($FullMemory) { Write-Warning 'Full dumps contain private memory, may require several GB, and must not be uploaded.' }
if ($NoClone) { Write-Warning 'Direct capture can temporarily pause Skyrim until the dump completes or its timeout cancels collection.' }
Write-Host "Capturing two local $dumpType dumps of SkyrimSE PID $capturePid into $captureRoot"
& $captureTool @captureArgs
$captureExitCode = $LASTEXITCODE
$validation = Get-HangCaptureValidation -LiteralPath $captureRoot -RequireFullMemory:$FullMemory
$validation.Dumps | Select-Object FullName, Length, StreamCount, FullMemory, StructurallyValid, Error
if (-not $validation.Complete) {
    throw "Capture incomplete: $($validation.ValidCount) structurally valid dumps out of $($validation.DumpCount) files; expected 2. ProcDump exit code: $captureExitCode. Files preserved at $captureRoot. Do not retry until its output is reviewed."
}
if ($captureExitCode -ne 0) {
    Write-Warning "ProcDump exited with code $captureExitCode, but both dump files passed structural validation. The files are saved; review the warning before any retry."
}
Write-Host 'Both local dumps are saved and passed structural validation. This checks file structure, not whether they contain enough evidence to diagnose the freeze.'
