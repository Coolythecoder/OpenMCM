[CmdletBinding()]
param(
    [string] $ProjectRoot = (Join-Path $PSScriptRoot '..'),
    [string] $Python = 'python',
    [string] $Caprica
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
if (-not $Caprica) { $Caprica = Join-Path $ProjectRoot '.tools\caprica-0.3.0\Caprica.exe' }
$source = Join-Path $ProjectRoot 'src\compat\jaxonz-kicker'
$sdk = Join-Path $ProjectRoot 'src\papyrus'
$stubs = Join-Path $ProjectRoot 'vendor\papyrus-stubs'
$buildParent = [IO.Path]::GetFullPath((Join-Path $ProjectRoot 'build'))
$buildRoot = [IO.Path]::GetFullPath((Join-Path $buildParent 'kicker-compat'))
if (-not $buildRoot.StartsWith($buildParent.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Unsafe generated Kicker compatibility output.'
}
foreach ($directory in @($ProjectRoot, $buildParent, $buildRoot)) {
    if ((Test-Path -LiteralPath $directory) -and
        ((Get-Item -LiteralPath $directory).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing generated writes through linked directory: $directory"
    }
}
if (Test-Path -LiteralPath $buildRoot) {
    Remove-Item -LiteralPath $buildRoot -Recurse -Force
}
$data = Join-Path $buildRoot 'Data'
$compiled = Join-Path $data 'Scripts'
$installedSource = Join-Path $data 'Source\Scripts'
New-Item -ItemType Directory -Path $compiled,$installedSource -Force | Out-Null
foreach ($name in @('JaxonzMCMKicker', 'JaxonzSKSEVersionCheckScript')) {
    $script = Join-Path $source "$name.psc"
    & $Caprica --game=skyrim --ignorecwd "--output=$compiled" "--import=$source" "--import=$sdk" "--import=$stubs" `
        "--flags=$(Join-Path $stubs 'TESV_Papyrus_Flags.flg')" --release --final `
        --skyrim-allow-unknown-events-on-non-native-class=true $script
    if ($LASTEXITCODE -ne 0) { throw "Kicker compatibility compilation failed: $name" }
    Copy-Item -LiteralPath $script -Destination $installedSource
}
& $Python -B (Join-Path $ProjectRoot 'tools\sanitize_papyrus_metadata.py') $compiled
if ($LASTEXITCODE -ne 0) { throw 'Kicker PEX metadata normalization failed.' }
& $Python -B (Join-Path $ProjectRoot 'tools\repair_papyrus_identifiers.py') `
    (Join-Path $compiled 'JaxonzMCMKicker.pex')
if ($LASTEXITCODE -ne 0) { throw 'Kicker PEX identifier repair failed.' }
& $Python -B (Join-Path $ProjectRoot 'tools\check_kicker.py') $data
if ($LASTEXITCODE -ne 0) { throw 'Kicker compatibility payload validation failed.' }
Write-Host "Kicker compatibility Data: $data"
