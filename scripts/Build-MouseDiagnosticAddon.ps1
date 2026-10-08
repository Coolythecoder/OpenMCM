[CmdletBinding()]
param([switch] $MouseUpdate)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$archiveName = if ($MouseUpdate) { 'OpenMCM-Mouse-Update-rc6.zip' } else { 'OpenMCM-Mouse-Diagnostics-1.zip' }
$requiredVersion = if ($MouseUpdate) { '1.0.1-rc.6' } else { '1.0.1-diagnostic.1' }
$readmeName = if ($MouseUpdate) { 'MOUSE-UPDATE-RC6-README.md' } else { 'MOUSE-PROBE-README.md' }
$archivePath = Join-Path $projectRoot "dist/$archiveName"
$files = [ordered]@{
    'Data/Interface/quest_journal.swf' = 'build/staging/Data/Interface/quest_journal.swf'
    'Data/Scripts/OpenMCM_ConfigMenu.pex' = 'build/staging/Data/Scripts/OpenMCM_ConfigMenu.pex'
    'README-MOUSE-ADDON.md' = "docs/diagnostics/$readmeName"
    'LICENSE' = 'LICENSE'
}
$manifest = Get-Content -LiteralPath (Join-Path $projectRoot 'build/staging/OpenMCM_BUILD.json') -Raw | ConvertFrom-Json
if ($manifest.version -ne $requiredVersion) {
    throw "Build $requiredVersion successfully before packaging this addon."
}
foreach ($relative in $files.Values) {
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $relative) -PathType Leaf)) {
        throw "Missing diagnostic input: $relative"
    }
}
# Create mode refuses an existing archive; do not silently replace a capture build.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::Open($archivePath, [IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($entry in $files.GetEnumerator()) {
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive,
            (Join-Path $projectRoot $entry.Value), $entry.Key,
            [IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
} finally {
    $archive.Dispose()
}
$verify = [IO.Compression.ZipFile]::OpenRead($archivePath)
try {
    if ($verify.Entries.Count -ne $files.Count) { throw 'Unexpected addon contents.' }
    foreach ($entry in $verify.Entries) {
        if (-not $files.Contains($entry.FullName)) { throw "Unexpected entry: $($entry.FullName)" }
        $stream = $entry.Open()
        $hasher = [Security.Cryptography.SHA256]::Create()
        try {
            $actual = [BitConverter]::ToString($hasher.ComputeHash($stream)).Replace('-', '')
        } finally { $stream.Dispose(); $hasher.Dispose() }
        $expected = (Get-FileHash -LiteralPath (Join-Path $projectRoot $files[$entry.FullName]) -Algorithm SHA256).Hash
        if ($actual -ne $expected) { throw "ZIP payload mismatch: $($entry.FullName)" }
        Write-Host "$($entry.FullName): $actual"
    }
} finally { $verify.Dispose() }
Write-Host "Interface addon: $archivePath"
Write-Host 'Not deployed. Contains no DLL, INI, ESP or registration-manager change.'
