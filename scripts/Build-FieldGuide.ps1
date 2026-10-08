[CmdletBinding()]
param(
    [string] $ProjectRoot = (Join-Path $PSScriptRoot '..'),
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$')]
    [string] $Version = '1.0.0',
    [string] $Python = 'python',
    [string] $Caprica,
    [string] $Spriggit
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
if (-not $Caprica) { $Caprica = Join-Path $ProjectRoot '.tools\caprica-0.3.0\Caprica.exe' }
if (-not $Spriggit) { $Spriggit = Join-Path $ProjectRoot '.tools\spriggit-0.41.0\Spriggit.CLI.exe' }
$exampleRoot = Join-Path $ProjectRoot 'examples\field-guide'
$source = Join-Path $exampleRoot 'OpenMCM_FieldGuide.psc'
$sdk = Join-Path $ProjectRoot 'src\papyrus'
$stubs = Join-Path $ProjectRoot 'vendor\papyrus-stubs'
foreach ($required in @($Caprica, $Spriggit, $source, (Join-Path $exampleRoot 'README.md'),
        (Join-Path $sdk 'OpenMCM_ConfigBase.psc'), (Join-Path $stubs 'TESV_Papyrus_Flags.flg'))) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required source/tool missing: $required. Use a prepared OpenMCM checkout."
    }
}
$buildParent = [IO.Path]::GetFullPath((Join-Path $ProjectRoot 'build'))
$buildRoot = [IO.Path]::GetFullPath((Join-Path $buildParent 'field-guide'))
if (-not $buildRoot.StartsWith($buildParent.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unsafe generated Field Guide build path.'
}
foreach ($directory in @($ProjectRoot, $buildParent, $buildRoot)) {
    if ((Test-Path -LiteralPath $directory) -and
        ((Get-Item -LiteralPath $directory).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing generated writes through linked directory: $directory"
    }
}
if (Test-Path -LiteralPath $buildRoot) {
    # This one exact validated generated directory belongs to this builder.
    Remove-Item -LiteralPath $buildRoot -Recurse -Force
}
$staging = Join-Path $buildRoot 'package'
$data = Join-Path $staging 'Data'
$scripts = Join-Path $data 'Scripts'
New-Item -ItemType Directory -Path $scripts,(Join-Path $data 'Seq'),
    (Join-Path $data 'Source\Scripts'),(Join-Path $staging 'Docs'),
    (Join-Path $staging 'Source\Plugin'),(Join-Path $staging 'Source\scripts'),
    (Join-Path $staging 'Source\tools') -Force | Out-Null

Push-Location $exampleRoot
try {
    & $Caprica --game=skyrim "--output=$scripts" "--import=$sdk" "--import=$stubs" `
        "--flags=$(Join-Path $stubs 'TESV_Papyrus_Flags.flg')" --release --final `
        --skyrim-allow-unknown-events-on-non-native-class=true $source
    if ($LASTEXITCODE -ne 0) { throw 'Field Guide Papyrus compilation failed.' }
}
finally { Pop-Location }
& $Python -B (Join-Path $ProjectRoot 'tools\sanitize_papyrus_metadata.py') `
    (Join-Path $scripts 'OpenMCM_FieldGuide.pex')
if ($LASTEXITCODE -ne 0) { throw 'Field Guide PEX metadata normalization failed.' }
& $Python -B (Join-Path $ProjectRoot 'tools\repair_papyrus_identifiers.py') `
    (Join-Path $scripts 'OpenMCM_FieldGuide.pex')
if ($LASTEXITCODE -ne 0) { throw 'Field Guide PEX identifier repair failed.' }

$oldAppData = $env:APPDATA
try {
    $env:APPDATA = Join-Path $ProjectRoot '.tools\spriggit-appdata'
    & $Spriggit deserialize -i (Join-Path $exampleRoot 'plugin\OpenMCM_FieldGuide.esp') `
        -o (Join-Path $data 'OpenMCM_FieldGuide.esp') -p 'Spriggit.Yaml.Skyrim' -v '0.41.0'
    if ($LASTEXITCODE -ne 0) { throw 'Field Guide plugin build failed.' }
}
finally { $env:APPDATA = $oldAppData }

# Two masters, then this plugin: own start-enabled quest 02000800.
[IO.File]::WriteAllBytes((Join-Path $data 'Seq\OpenMCM_FieldGuide.seq'), [byte[]]@(0x00,0x08,0x00,0x02))
Copy-Item -LiteralPath $source -Destination (Join-Path $data 'Source\Scripts')
Copy-Item -LiteralPath (Join-Path $exampleRoot 'README.md') -Destination (Join-Path $staging 'README.md')
Copy-Item -LiteralPath (Join-Path $exampleRoot 'LICENSE') -Destination (Join-Path $staging 'LICENSE')
Copy-Item -LiteralPath (Join-Path $exampleRoot 'BUILDING.md') -Destination (Join-Path $staging 'Docs\BUILDING.md')
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'docs\OpenMCM-API.md') -Destination (Join-Path $staging 'Docs')
Copy-Item -LiteralPath (Join-Path $exampleRoot 'plugin\OpenMCM_FieldGuide.esp') `
    -Destination (Join-Path $staging 'Source\Plugin') -Recurse
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'scripts\Build-FieldGuide.ps1') -Destination (Join-Path $staging 'Source\scripts')
foreach ($tool in @('check_field_guide.py', 'check_mcm_contract.py', 'check_openmcm_api.py', 'repair_papyrus_identifiers.py', 'sanitize_papyrus_metadata.py')) {
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "tools\$tool") -Destination (Join-Path $staging 'Source\tools')
}
$manifest = Join-Path $staging 'OpenMCM_SHA256SUMS.txt'
$lines = @(Get-ChildItem -LiteralPath $staging -Recurse -File | Sort-Object FullName | ForEach-Object {
    "$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash)  $($_.FullName.Substring($staging.Length + 1).Replace('\', '/'))"
})
[IO.File]::WriteAllLines($manifest, $lines, [Text.UTF8Encoding]::new($false))
& $Python -B (Join-Path $ProjectRoot 'tools\check_field_guide.py') $staging
if ($LASTEXITCODE -ne 0) { throw 'Field Guide staged payload validation failed.' }

$dist = [IO.Path]::GetFullPath((Join-Path $ProjectRoot 'dist'))
$archive = [IO.Path]::GetFullPath((Join-Path $dist "OpenMCM-Field-Guide-$Version.zip"))
if (-not $archive.StartsWith($dist.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unsafe Field Guide archive path.'
}
if ((Test-Path -LiteralPath $dist) -and
    ((Get-Item -LiteralPath $dist).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw 'Refusing archive write through a linked dist directory.'
}
New-Item -ItemType Directory -Path $dist -Force | Out-Null
# Overwrite only this explicitly named generated example archive, never a host package.
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $archive -CompressionLevel Optimal -Force
& $Python -B (Join-Path $ProjectRoot 'tools\check_field_guide.py') $archive
if ($LASTEXITCODE -ne 0) { throw 'Field Guide final ZIP validation failed.' }
Write-Host "Field Guide package: $archive"
Write-Host "SHA256: $((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash)"
Write-Host 'Structural checks passed; in-game verification is still required. No installed game files were changed.'
