[CmdletBinding()]
param(
    [string] $SkyrimPath = $env:SKYRIM_SE_PATH,
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$')]
    [string] $Version = '2.1.0',
    [ValidateSet('Fomod', 'Standalone')]
    [string] $PackageFormat = 'Fomod',
    [switch] $SkipTests
)

$ErrorActionPreference = 'Stop'
& (Join-Path $PSScriptRoot 'scripts\Build-OpenMCM.ps1') `
    -SkyrimPath $SkyrimPath `
    -Version $Version `
    -PackageFormat $PackageFormat `
    -SkipTests:$SkipTests
