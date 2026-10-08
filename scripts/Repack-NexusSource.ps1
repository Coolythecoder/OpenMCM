[CmdletBinding()]
param(
    [string] $ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string] $Version = '2.1.0',
    [string] $InputPackage = (Join-Path (Split-Path -Parent $PSScriptRoot) 'build\fomod'),
    [string] $StageName = 'nexus-source-repack-2.1.0',
    [string] $ArchiveName = 'OpenMCM-2.1.0-Nexus-Source-FOMOD.zip'
)

# Packaging-only repair: preserve all existing archives and runtime payloads.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
if ($StageName -notmatch '^[A-Za-z0-9.-]+$' -or $ArchiveName -notmatch '^[A-Za-z0-9.-]+\.zip$') {
    throw 'Output names must be simple names, not paths.'
}
$stage = Join-Path $ProjectRoot "build\$StageName"
$archive = Join-Path $ProjectRoot "dist\$ArchiveName"
if ((Test-Path -LiteralPath $stage) -or (Test-Path -LiteralPath $archive)) {
    throw 'Output already exists. Refusing to overwrite any prior package or staging folder.'
}
& python -B (Join-Path $ProjectRoot 'tools\check_fomod_package.py') $InputPackage
if ($LASTEXITCODE -ne 0) { throw 'Original package does not validate; cannot safely repack.' }
$metadata = Get-Content -LiteralPath (Join-Path $InputPackage 'OpenMCM_BUILD.json') -Raw | ConvertFrom-Json
if ($metadata.version -ne $Version) { throw 'Requested version differs from the verified binary package.' }
Copy-Item -LiteralPath $InputPackage -Destination $stage -Recurse
foreach ($name in @('README.md', 'README.txt', 'LICENSE', 'LICENSE.txt', 'THIRD_PARTY_NOTICES.md')) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot $name) -Destination (Join-Path $stage $name) -Force
}
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'licenses') -Destination $stage -Recurse
foreach ($name in @('Nexus-Publication-Checklist.md', 'Jaxonz-MCM-Kicker.md')) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "docs\$name") -Destination (Join-Path $stage "docs\$name") -Force
}

$sourceRelative = "source/OpenMCM-$Version-Source.zip"
$sourceArchive = Join-Path $stage $sourceRelative
$browserArchive = Join-Path $InputPackage $metadata.browserIntegration.sourceArchive
& python -B (Join-Path $ProjectRoot 'tools\package_openmcm_source.py') `
    --project-root $ProjectRoot --browser-source $browserArchive --output $sourceArchive --version $Version
if ($LASTEXITCODE -ne 0) { throw 'Complete source packaging failed.' }
$metadata | Add-Member -NotePropertyName correspondingSource -NotePropertyValue ([ordered]@{
    archive = $sourceRelative
    sha256 = (Get-FileHash -LiteralPath $sourceArchive -Algorithm SHA256).Hash
    scope = 'complete OpenMCM project source plus pinned browser dependencies'
    license = 'GPL-3.0-or-later for original OpenMCM code; see third-party notices'
}) -Force
[IO.File]::WriteAllText((Join-Path $stage 'OpenMCM_BUILD.json'), ($metadata | ConvertTo-Json -Depth 8),
    [Text.UTF8Encoding]::new($false))
$manifest = Join-Path $stage 'OpenMCM_SHA256SUMS.txt'
$lines = @(Get-ChildItem -LiteralPath $stage -Recurse -File |
    Where-Object { $_.FullName -ne $manifest } | Sort-Object FullName | ForEach-Object {
        $relative = $_.FullName.Substring($stage.Length + 1).Replace('\', '/')
        "$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash)  $relative"
    })
[IO.File]::WriteAllLines($manifest, $lines, [Text.UTF8Encoding]::new($false))
& python -B (Join-Path $ProjectRoot 'tools\check_fomod_package.py') $stage
if ($LASTEXITCODE -ne 0) { throw 'Source-inclusive staging validation failed.' }

# Verify repacking did not modify one byte of any installed component.
foreach ($tree in @('modes', 'components')) {
    $originalRoot = Join-Path $InputPackage $tree
    $originalFiles = @(Get-ChildItem -LiteralPath $originalRoot -Recurse -File)
    $repackedFiles = @(Get-ChildItem -LiteralPath (Join-Path $stage $tree) -Recurse -File)
    if ($originalFiles.Count -ne $repackedFiles.Count) { throw "Runtime inventory changed in $tree." }
    foreach ($file in $originalFiles) {
        $relative = $file.FullName.Substring($originalRoot.Length + 1)
        $repacked = Join-Path (Join-Path $stage $tree) $relative
        if ((Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath $repacked).Hash) {
            throw "Runtime payload changed: $tree/$relative"
        }
    }
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($stage, $archive, [IO.Compression.CompressionLevel]::Optimal, $false)
& python -B (Join-Path $ProjectRoot 'tools\check_fomod_package.py') $archive
if ($LASTEXITCODE -ne 0) { throw 'Final archive validation failed.' }
& (Join-Path $ProjectRoot 'scripts\Test-FomodXml.ps1') -ArchivePath $archive
Get-Item -LiteralPath $archive | Select-Object FullName, Length
Get-FileHash -LiteralPath $archive -Algorithm SHA256
