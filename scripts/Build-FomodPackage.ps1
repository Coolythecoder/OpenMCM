[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $ProjectRoot,
    [Parameter(Mandatory)] [string] $StagingRoot,
    [Parameter(Mandatory)] [string] $Version,
    [Parameter(Mandatory)] [string] $Python,
    [Parameter(Mandatory)] [string] $Spriggit,
    [switch] $SkipTests
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# These are generated build-only directories, never installed game/mod-manager paths.
$fomodBuildRoot = [IO.Path]::GetFullPath((Join-Path $ProjectRoot 'build'))
if ((Get-Item -LiteralPath $fomodBuildRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Refusing to reset generated FOMOD outputs under a linked build directory.'
}
$inputRoot = Join-Path $fomodBuildRoot 'fomod-inputs'
$outputRoot = Join-Path $fomodBuildRoot 'fomod'
foreach ($generated in @($inputRoot, $outputRoot)) {
    $resolved = [IO.Path]::GetFullPath($generated)
    if (-not $resolved.StartsWith($fomodBuildRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unsafe FOMOD output path: $resolved"
    }
    if (Test-Path -LiteralPath $resolved) {
        if ((Get-Item -LiteralPath $resolved).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to reset a linked FOMOD output: $resolved"
        }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}
$standaloneData = Join-Path $inputRoot 'standalone\Data'
$skyuiData = Join-Path $inputRoot 'skyui\Data'
$nativeData = Join-Path $inputRoot 'native\Data'
$browserData = Join-Path $inputRoot 'browser\Data'
New-Item -ItemType Directory -Path $standaloneData,$skyuiData,$nativeData,$browserData -Force | Out-Null
$builtData = Join-Path $StagingRoot 'Data'

foreach ($entry in Get-ChildItem -LiteralPath $builtData) {
    if ($entry.Name -ne 'SKSE') {
        Copy-Item -LiteralPath $entry.FullName -Destination $standaloneData -Recurse
    }
}
New-Item -ItemType Directory -Path (Join-Path $nativeData 'SKSE\Plugins'),(Join-Path $browserData 'SKSE\Plugins') -Force | Out-Null
foreach ($nativeName in @('OpenMCMRuntime.dll', 'OpenMCMRuntime.ini')) {
    Copy-Item -LiteralPath (Join-Path $builtData "SKSE\Plugins\$nativeName") -Destination (Join-Path $nativeData 'SKSE\Plugins')
}
Copy-Item -LiteralPath (Join-Path $builtData 'SKSE\Plugins\OpenMCMBrowser.dll') -Destination (Join-Path $browserData 'SKSE\Plugins')

# Only the MCM implementation is allowed to override SkyUI. In particular do
# not replace its ESP, global lifecycle scripts, settings provider or translations.
$coexistPaths = @(
    'Interface\quest_journal.swf',
    'Scripts\SKI_ConfigBase.pex',
    'Scripts\SKI_ConfigManager.pex',
    'Scripts\OpenMCM_ConfigMenu.pex',
    'Scripts\OpenMCM.pex',
    'Scripts\OpenMCM_ConfigBase.pex',
    'Source\Scripts\SKI_ConfigBase.psc',
    'Source\Scripts\SKI_ConfigManager.psc',
    'Source\Scripts\OpenMCM_ConfigMenu.psc',
    'Source\Scripts\OpenMCM.psc',
    'Source\Scripts\OpenMCM_ConfigBase.psc'
)
foreach ($relative in $coexistPaths) {
    $destination = Join-Path $skyuiData $relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $builtData $relative) -Destination $destination
}

$previousAppData = $env:APPDATA
try {
    $env:APPDATA = Join-Path $ProjectRoot '.tools\spriggit-appdata'
    & $Spriggit deserialize -i (Join-Path $ProjectRoot 'src\plugin-coexist\OpenMCM.esp') `
        -o (Join-Path $skyuiData 'OpenMCM.esp') -p 'Spriggit.Yaml.Skyrim' -v '0.41.0' |
        ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw 'Building coexistence status plugin failed.' }
}
finally { $env:APPDATA = $previousAppData }

# Two masters, one local status quest. The sole manager stays in real SkyUI.
New-Item -ItemType Directory -Path (Join-Path $skyuiData 'Seq') -Force | Out-Null
[IO.File]::WriteAllBytes((Join-Path $skyuiData 'Seq\OpenMCM.seq'), [byte[]]@(0x00,0x08,0x00,0x02))

if (-not $SkipTests) {
    & $Python -B (Join-Path $ProjectRoot 'tools\check_mcm_contract.py') $standaloneData --profile release |
        ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw 'Standalone selected-install validation failed.' }
    & $Python -B (Join-Path $ProjectRoot 'tools\check_openmcm_api.py') $standaloneData |
        ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw 'Standalone opt-in API validation failed.' }
    & $Python -B (Join-Path $ProjectRoot 'tools\check_skyui_coexist.py') $skyuiData |
        ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw 'SkyUI coexistence selected-install validation failed.' }
}
# Compile and validate the runnable teaching example from this same checkout.
# It is one optional choice in the full release, not a separately required add-on.
& (Join-Path $PSScriptRoot 'Build-FieldGuide.ps1') -ProjectRoot $ProjectRoot `
    -Python $Python -Spriggit $Spriggit | ForEach-Object { Write-Host $_ }
$fieldGuidePackage = Join-Path $ProjectRoot 'build\field-guide\package'
& (Join-Path $PSScriptRoot 'Build-KickerCompatibility.ps1') -ProjectRoot $ProjectRoot `
    -Python $Python | ForEach-Object { Write-Host $_ }
$kickerData = Join-Path $ProjectRoot 'build\kicker-compat\Data'
& $Python -B (Join-Path $ProjectRoot 'tools\build_fomod_installer.py') `
    --standalone-data $standaloneData --skyui-data $skyuiData --native-data $nativeData --browser-data $browserData `
    --field-guide-package $fieldGuidePackage --kicker-data $kickerData `
    --output $outputRoot --version $Version | ForEach-Object { Write-Host $_ }
if ($LASTEXITCODE -ne 0) { throw 'FOMOD assembly failed.' }

foreach ($entry in Get-ChildItem -LiteralPath $StagingRoot) {
    if ($entry.Name -eq 'examples') {
        # The assembled Field Guide already contains its validated package
        # documentation and editable source. Do not merge a second layout into it.
        foreach ($example in Get-ChildItem -LiteralPath $entry.FullName) {
            if ($example.Name -ne 'field-guide') {
                Copy-Item -LiteralPath $example.FullName -Destination (Join-Path $outputRoot 'examples') -Recurse
            }
        }
    }
    elseif ($entry.Name -notin @('Data', 'OpenMCM_SHA256SUMS.txt')) {
        Copy-Item -LiteralPath $entry.FullName -Destination $outputRoot -Recurse
    }
}
$metadataPath = Join-Path $outputRoot 'OpenMCM_BUILD.json'
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'docs\Jaxonz-MCM-Kicker.md') -Destination (Join-Path $outputRoot 'docs')
$metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
$metadata | Add-Member -NotePropertyName 'jaxonzKicker' -NotePropertyValue ([ordered]@{
    version = '1.0.1'
    requiresPlugin = 'JaxonzMCMKicker.esp'
    requiresManagerMethod = 'OpenMCM_TryForceReset'
    dataPath = 'components/jaxonz-kicker/Data'
    installedByDefault = $false
    detectionRecommended = $true
    inGameVerification = 'not verified'
}) -Force
$metadata | Add-Member -NotePropertyName 'fieldGuide' -NotePropertyValue ([ordered]@{
    version = '1.0.0'
    installedByDefault = $false
    dataPath = 'components/field-guide/Data'
    authorFilesPath = 'examples/field-guide'
    inGameVerification = 'not verified'
}) -Force
[IO.File]::WriteAllText($metadataPath, ($metadata | ConvertTo-Json -Depth 8), [Text.UTF8Encoding]::new($false))
return $outputRoot
