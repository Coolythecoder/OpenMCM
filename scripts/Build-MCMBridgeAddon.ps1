[CmdletBinding()]
param(
    [string] $ProjectRoot = (Join-Path $PSScriptRoot '..'),
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$')]
    [string] $Version = '0.1.0',
    [string] $Python = 'python',
    [string] $Caprica,
    [string] $BridgeSource
)

# Build only the basic SDK add-on. This script does not download tools, build
# OpenMCM's host, install game files, or replace any existing release archive.
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
$distRoot = [IO.Path]::GetFullPath((Join-Path $ProjectRoot 'dist'))
$archive = [IO.Path]::GetFullPath((Join-Path $distRoot "OpenMCM-MCM-Bridge-Addon-$Version.zip"))
if (-not $archive.StartsWith($distRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unsafe MCM Bridge add-on archive path.'
}
if (Test-Path -LiteralPath $archive) {
    throw "Refusing to overwrite an existing MCM Bridge add-on archive: $archive"
}

function Assert-RegularPath {
    param([Parameter(Mandatory)] [string] $Path, [switch] $Directory)
    $item = Get-Item -LiteralPath $Path -ErrorAction Stop
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Refusing linked build input/output: $Path"
    }
    if ($Directory -ne $item.PSIsContainer) {
        throw "Wrong build input/output type: $Path"
    }
}

function Write-ChecksumManifest {
    param([Parameter(Mandatory)] [string] $Root)
    $manifest = Join-Path $Root 'SHA256SUMS.txt'
    $lines = @(Get-ChildItem -LiteralPath $Root -Recurse -File |
        Where-Object { $_.FullName -ne $manifest } | Sort-Object FullName | ForEach-Object {
            "$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash)  $($_.FullName.Substring($Root.Length + 1).Replace('\', '/'))"
        })
    [IO.File]::WriteAllLines($manifest, $lines, [Text.UTF8Encoding]::new($false))
}

function Copy-SourceFile {
    param([Parameter(Mandatory)] [string] $InputFile, [Parameter(Mandatory)] [string] $Relative)
    Assert-RegularPath -Path $InputFile
    $target = [IO.Path]::GetFullPath((Join-Path $sourceRoot $Relative))
    if (-not $target.StartsWith($sourceRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe source package path: $Relative"
    }
    if (Test-Path -LiteralPath $target) { throw "Duplicate source package path: $Relative" }
    New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
    Copy-Item -LiteralPath $InputFile -Destination $target
}

Assert-RegularPath -Path $ProjectRoot -Directory
if (Test-Path -LiteralPath $distRoot) { Assert-RegularPath -Path $distRoot -Directory }
if (-not $Caprica) { $Caprica = Join-Path $ProjectRoot '.tools\caprica-0.3.0\Caprica.exe' }
if (-not $BridgeSource) {
    $BridgeSource = Join-Path $ProjectRoot '.tools\mcm-bridge-reference'
    if (-not (Test-Path -LiteralPath $BridgeSource -PathType Container)) {
        $BridgeSource = Join-Path $ProjectRoot 'upstream\mcm-bridge'
    }
}
$BridgeSource = [IO.Path]::GetFullPath($BridgeSource)
$adapterRoot = Join-Path $ProjectRoot 'src\compat\mcm-bridge'
$compileImports = Join-Path $adapterRoot 'compile-imports'
$stubs = Join-Path $ProjectRoot 'vendor\papyrus-stubs'
$bridgeHost = Join-Path $BridgeSource 'scripts\Source\host'
$bridgeNative = Join-Path $BridgeSource 'scripts\Source'
foreach ($directory in @($BridgeSource, $adapterRoot, $compileImports, $stubs, $bridgeHost, $bridgeNative)) {
    Assert-RegularPath -Path $directory -Directory
}
foreach ($required in @($Caprica, (Join-Path $ProjectRoot 'LICENSE.txt'),
        (Join-Path $adapterRoot 'README.md'), (Join-Path $adapterRoot 'THIRD_PARTY_NOTICES.md'),
        (Join-Path $adapterRoot 'upstream.json'), (Join-Path $stubs 'TESV_Papyrus_Flags.flg'),
        (Join-Path $ProjectRoot 'tools\check_mcm_bridge_addon.py'))) {
    Assert-RegularPath -Path $required
}

$bridgeCommit = 'c039e67e9455ab9b21ba3024d8f6b3b157a511e2'
$pins = Get-Content -LiteralPath (Join-Path $adapterRoot 'upstream.json') -Raw | ConvertFrom-Json
if ($pins.version -ne '1.1.0' -or $pins.commit -ne $bridgeCommit) {
    throw 'MCM Bridge import metadata must pin the reviewed 1.1.0 commit.'
}
$expectedImports = @('scripts/Source/MCMBridgeNative.psc',
    'scripts/Source/host/MCMBridgeRegistry.psc', 'scripts/Source/host/SKI_ConfigBase.psc',
    'scripts/Source/host/SKI_ConfigManager.psc', 'scripts/Source/host/SKI_PlayerLoadGameAlias.psc',
    'scripts/Source/host/SKI_QuestBase.psc', 'LICENSE', 'THIRD_PARTY_NOTICES.md')
$pinNames = @($pins.files.PSObject.Properties.Name)
if (@(Compare-Object ($expectedImports | Sort-Object) ($pinNames | Sort-Object)).Count -ne 0) {
    throw 'MCM Bridge pin inventory must contain exactly the six facade scripts and upstream notices.'
}
foreach ($relative in $expectedImports) {
    $inputFile = Join-Path $BridgeSource $relative
    Assert-RegularPath -Path $inputFile
    $expectedHash = [string] $pins.files.PSObject.Properties[$relative].Value
    if ($expectedHash -notmatch '^[0-9A-Fa-f]{64}$' -or
        (Get-FileHash -LiteralPath $inputFile -Algorithm SHA256).Hash -ne $expectedHash) {
        throw "Pinned MCM Bridge import checksum mismatch: $relative"
    }
}

$buildParent = [IO.Path]::GetFullPath((Join-Path $ProjectRoot 'build'))
if (Test-Path -LiteralPath $buildParent) { Assert-RegularPath -Path $buildParent -Directory }
$buildRoot = [IO.Path]::GetFullPath((Join-Path $buildParent ('mcm-bridge-addon-' + [Guid]::NewGuid().ToString('N'))))
if (-not $buildRoot.StartsWith($buildParent.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unsafe MCM Bridge add-on build path.'
}
if (Test-Path -LiteralPath $buildRoot) { throw "Generated build directory already exists: $buildRoot" }
$staging = Join-Path $buildRoot 'package'
$sourceRoot = Join-Path $buildRoot 'source'
$scripts = Join-Path $staging 'Data\Scripts'
$installedSources = Join-Path $staging 'Data\Source\Scripts'
New-Item -ItemType Directory -Path $scripts,$installedSources,$sourceRoot,(Join-Path $staging 'source') -Force | Out-Null

# Adapter-first imports followed ONLY by Bridge's host/native facades and
# compile-time stubs. Never import src/papyrus (the separate OpenMCM host).
foreach ($script in @('OpenMCM', 'OpenMCM_ConfigBase')) {
    $source = Join-Path $adapterRoot "$script.psc"
    Assert-RegularPath -Path $source
    Push-Location $adapterRoot
    try {
        & $Caprica --game=skyrim "--output=$scripts" "--import=$adapterRoot" `
            "--import=$bridgeHost" "--import=$bridgeNative" "--import=$compileImports" "--import=$stubs" `
            "--flags=$(Join-Path $stubs 'TESV_Papyrus_Flags.flg')" --release --final `
            --skyrim-allow-unknown-events-on-non-native-class=true $source
        if ($LASTEXITCODE -ne 0) { throw "MCM Bridge adapter compilation failed: $script" }
    }
    finally { Pop-Location }
    $pex = Join-Path $scripts "$script.pex"
    & $Python -B (Join-Path $ProjectRoot 'tools\sanitize_papyrus_metadata.py') $pex
    if ($LASTEXITCODE -ne 0) { throw "Adapter metadata normalization failed: $script" }
    & $Python -B (Join-Path $ProjectRoot 'tools\repair_papyrus_identifiers.py') $pex
    if ($LASTEXITCODE -ne 0) { throw "Adapter identifier repair failed: $script" }
    Copy-Item -LiteralPath $source -Destination $installedSources
}
foreach ($name in @('README.md', 'THIRD_PARTY_NOTICES.md')) {
    Copy-Item -LiteralPath (Join-Path $adapterRoot $name) -Destination $staging
}
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'LICENSE.txt') -Destination $staging

# Explicit reproducible-source inventory, never a copy of the workspace/cache.
Copy-SourceFile -InputFile (Join-Path $ProjectRoot 'LICENSE.txt') -Relative 'LICENSE.txt'
foreach ($file in Get-ChildItem -LiteralPath $adapterRoot -Recurse -File) {
    $relative = $file.FullName.Substring($ProjectRoot.Length + 1)
    Copy-SourceFile -InputFile $file.FullName -Relative $relative
}
foreach ($relative in @('scripts\Build-MCMBridgeAddon.ps1',
        'tools\check_mcm_bridge_addon.py', 'tools\check_mcm_contract.py',
        'tools\sanitize_papyrus_metadata.py', 'tools\repair_papyrus_identifiers.py',
        'tests\test_bridge_addon_package.py', 'tests\test_bridge_sdk.py',
        'tests\test_bridge_addon_build.py', 'licenses\OpenMCM-previous-MIT.txt',
        'src\papyrus\OpenMCM.psc', 'src\papyrus\OpenMCM_ConfigBase.psc')) {
    Copy-SourceFile -InputFile (Join-Path $ProjectRoot $relative) -Relative $relative
}
foreach ($file in Get-ChildItem -LiteralPath $stubs -Recurse -File) {
    $relative = $file.FullName.Substring($ProjectRoot.Length + 1)
    Copy-SourceFile -InputFile $file.FullName -Relative $relative
}
foreach ($relative in $expectedImports) {
    Copy-SourceFile -InputFile (Join-Path $BridgeSource $relative) -Relative "upstream/mcm-bridge/$relative"
}
Write-ChecksumManifest -Root $sourceRoot
$sourceRelative = "source/OpenMCM-MCM-Bridge-Addon-$Version-Source.zip"
$sourceArchive = Join-Path $staging $sourceRelative
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::CreateFromDirectory($sourceRoot, $sourceArchive, [IO.Compression.CompressionLevel]::Optimal, $false)
$metadata = [ordered]@{
    project = 'OpenMCM MCM Bridge Add-on'
    version = $Version
    openMCMApiVersion = 1
    host = 'MCM Bridge'
    bridgeVersion = '1.1.0'
    bridgeCommit = $bridgeCommit
    capabilities = @('named_options')
    apiEnabled = $false
    inGameVerified = $false
    sourceArchive = $sourceRelative
    sourceSha256 = (Get-FileHash -LiteralPath $sourceArchive -Algorithm SHA256).Hash
}
[IO.File]::WriteAllText((Join-Path $staging 'OpenMCM_BRIDGE_ADDON.json'),
    ($metadata | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
Write-ChecksumManifest -Root $staging
& $Python -B (Join-Path $ProjectRoot 'tools\check_mcm_bridge_addon.py') $staging
if ($LASTEXITCODE -ne 0) { throw 'MCM Bridge add-on staged package validation failed.' }

if (Test-Path -LiteralPath $distRoot) { Assert-RegularPath -Path $distRoot -Directory }
New-Item -ItemType Directory -Path $distRoot -Force | Out-Null
if (Test-Path -LiteralPath $archive) {
    throw "Refusing to overwrite an existing MCM Bridge add-on archive: $archive"
}
[IO.Compression.ZipFile]::CreateFromDirectory($staging, $archive, [IO.Compression.CompressionLevel]::Optimal, $false)
& $Python -B (Join-Path $ProjectRoot 'tools\check_mcm_bridge_addon.py') $archive
if ($LASTEXITCODE -ne 0) { throw 'MCM Bridge add-on final ZIP validation failed.' }
Write-Host "MCM Bridge add-on package: $archive"
Write-Host "SHA256: $((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash)"
Write-Host 'Structural checks passed; in-game verification is still required. No installed game files were changed.'
