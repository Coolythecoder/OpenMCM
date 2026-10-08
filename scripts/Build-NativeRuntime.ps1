[CmdletBinding()]
param(
    [string] $ProjectRoot = (Join-Path $PSScriptRoot '..'),
    [Parameter(Mandatory)]
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$')]
    [string] $Version
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function ConvertTo-OpenMCMPluginVersion {
    param(
        [Parameter(Mandatory)]
        [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$')]
        [string] $ReleaseVersion
    )

    # Match SKSE/CommonLib's major:8, minor:8, patch:12, build:4 packing.
    # Prerelease text belongs in the log string, not the numeric metadata.
    $nativeVersionParts = $ReleaseVersion.Split('-')[0].Split('.')
    $nativeMajor = [uint64]::Parse($nativeVersionParts[0])
    $nativeMinor = [uint64]::Parse($nativeVersionParts[1])
    $nativePatch = [uint64]::Parse($nativeVersionParts[2])
    if ($nativeMajor -gt 255 -or $nativeMinor -gt 255 -or $nativePatch -gt 4095) {
        throw 'Native plugin version exceeds SKSE packing limits (major/minor 255, patch 4095).'
    }
    $nativePacked = [uint32](($nativeMajor -shl 24) -bor ($nativeMinor -shl 16) -bor ($nativePatch -shl 4))
    if ($nativePacked -eq 0) {
        throw 'Native plugin version must be nonzero.'
    }
    return $nativePacked
}

# Validate before invoking the compiler or clearing any generated output.
$nativePluginVersion = ConvertTo-OpenMCMPluginVersion -ReleaseVersion $Version
$nativePluginVersionDefine = '0x{0:X8}' -f $nativePluginVersion
$nativeProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
$nativeBuildRoot = Join-Path $nativeProjectRoot 'build\native'
$nativeSource = Join-Path $nativeProjectRoot 'src\native\OpenMCMRuntime.cpp'
$nativeTests = Join-Path $nativeProjectRoot 'tests\native\test_precache_patch.cpp'
$nativeConfig = Join-Path $nativeProjectRoot 'src\native\OpenMCMRuntime.ini'
$nativeBatch = Join-Path $nativeProjectRoot 'scripts\Build-NativeRuntime.cmd'
foreach ($required in @($nativeSource, $nativeTests, $nativeConfig, $nativeBatch)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Native runtime build input is missing: $required"
    }
}

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path -LiteralPath $vswhere -PathType Leaf)) {
    throw 'Visual Studio Installer was not found. Install Visual Studio 2022 or newer (or Build Tools) with Desktop development with C++ and a Windows SDK.'
}
$nativeVisualStudio = & $vswhere -latest -products '*' `
    -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath
if ($LASTEXITCODE -ne 0 -or -not $nativeVisualStudio) {
    throw 'No Visual Studio C++ x64 toolchain was found. Install Desktop development with C++ and a Windows SDK.'
}
$nativeVcvars = Join-Path ([string]$nativeVisualStudio) 'VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path -LiteralPath $nativeVcvars -PathType Leaf)) {
    throw "The Visual Studio x64 compiler environment is missing: $nativeVcvars"
}

New-Item -ItemType Directory -Path $nativeBuildRoot -Force | Out-Null
$nativeDll = Join-Path $nativeBuildRoot 'OpenMCMRuntime.dll'
# Remove only exact generated outputs so an interrupted compiler cannot leave
# an old DLL or passing test executable looking like this build's output.
foreach ($generated in @('OpenMCMRuntime.dll', 'test_precache_patch.exe',
    'OpenMCMRuntime-headers.txt', 'OpenMCMRuntime-exports.txt',
    'OpenMCMRuntime-dependents.txt')) {
    $generatedPath = Join-Path $nativeBuildRoot $generated
    if (Test-Path -LiteralPath $generatedPath -PathType Leaf) {
        Remove-Item -LiteralPath $generatedPath -Force
    }
}

Write-Host "Building optional OpenMCMRuntime $Version and running native regression tests..."
Push-Location $nativeProjectRoot
try {
    # The first cmd argument is an unquoted relative path without spaces. cmd
    # therefore preserves the separate quoted absolute path arguments correctly.
    & $env:ComSpec /d /c scripts\Build-NativeRuntime.cmd `
        $nativeVcvars $nativeProjectRoot $nativeBuildRoot $Version $nativePluginVersionDefine 2>&1 |
        Tee-Object -FilePath (Join-Path $nativeBuildRoot 'build.log') |
        ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) {
        throw "Building/testing OpenMCMRuntime failed with exit code $LASTEXITCODE. See build/native/build.log."
    }
}
finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $nativeDll -PathType Leaf)) {
    throw 'The native compiler did not produce OpenMCMRuntime.dll.'
}
$nativeHeaders = Get-Content -LiteralPath (Join-Path $nativeBuildRoot 'OpenMCMRuntime-headers.txt') -Raw
$nativeExports = Get-Content -LiteralPath (Join-Path $nativeBuildRoot 'OpenMCMRuntime-exports.txt') -Raw
$nativeDependents = Get-Content -LiteralPath (Join-Path $nativeBuildRoot 'OpenMCMRuntime-dependents.txt') -Raw
if ($nativeHeaders -notmatch '(?im)^\s*8664 machine \(x64\)\s*$') {
    throw 'OpenMCMRuntime.dll is not an x64 PE image.'
}
foreach ($nativeExport in @('SKSEPlugin_Version', 'SKSEPlugin_Load')) {
    if ($nativeExports -notmatch ('(?m)\s' + [regex]::Escape($nativeExport) + '\s*$')) {
        throw "OpenMCMRuntime.dll is missing the required SKSE export '$nativeExport'."
    }
}
if ($nativeDependents -match '(?i)\b(?:vcruntime|msvcp|ucrtbase)[^\s]*\.dll\b') {
    throw 'OpenMCMRuntime.dll unexpectedly depends on a separately installed C++ runtime; compile with /MT.'
}

[pscustomobject]@{
    DllPath = $nativeDll
    IniPath = $nativeConfig
    Sha256 = (Get-FileHash -LiteralPath $nativeDll -Algorithm SHA256).Hash
    ConfigSha256 = (Get-FileHash -LiteralPath $nativeConfig -Algorithm SHA256).Hash
    SupportedGameRuntime = '1.7.104.0'
    PluginVersion = $nativePluginVersion
}
