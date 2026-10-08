[CmdletBinding()]
param(
    [string] $ProjectRoot = (Join-Path $PSScriptRoot '..'),
    [Parameter(Mandatory)]
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$')]
    [string] $Version,
    [string] $Xmake = '',
    [string] $CommonLib = '',
    [string] $Python = '',
    [switch] $SkipSourceArchive
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$browserRoot = [IO.Path]::GetFullPath($ProjectRoot)
$browserSource = Join-Path $browserRoot 'src\browser-native'
$browserOutput = Join-Path $browserRoot 'build\browser-native'
if (-not $Xmake) { $Xmake = Join-Path $browserRoot '.tools\xmake-3.1.1\xmake\xmake.exe' }
if (-not $CommonLib) { $CommonLib = Join-Path $browserRoot '.tools\CommonLibSSE-NG-7.5.1' }
if (-not $Python) {
    $browserPython = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $browserPython) { throw 'Python 3 is required for the read-only DLL checker/source package.' }
    $Python = $browserPython.Source
}
foreach ($required in @($Xmake, (Join-Path $CommonLib 'xmake.lua'), (Join-Path $browserSource 'Bridge.cpp'))) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing browser build input: $required. See src/browser-native/README.md." }
}
$browserVersionParts = $Version.Split('-')[0].Split('.')
if ([uint64]$browserVersionParts[0] -gt 255 -or [uint64]$browserVersionParts[1] -gt 255 -or [uint64]$browserVersionParts[2] -gt 4095) {
    throw 'Version exceeds SKSE numeric packing limits.'
}
$browserXmakeVersion = @(& $Xmake --version)
if ($LASTEXITCODE -ne 0 -or $browserXmakeVersion[0] -notmatch 'v3\.1\.1\b') { throw 'xmake 3.1.1 is required.' }
if (Test-Path -LiteralPath (Join-Path $CommonLib '.git')) {
    $browserCommit = (& git -C $CommonLib rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0 -or $browserCommit -ne 'bedcb1e05418baba7b316a650b6180c2dd6007a8') { throw 'CommonLib must be the pinned 7.5.1 revision.' }
}
foreach ($fingerprint in @(
    @('xmake.lua', '439A011CAED965E4D0B555AE63761319EDBFBA6948C5F93221597F3E72CDA89B'),
    @('include\SKSE\Version.h', 'E3BC95B877ED9FEA8E21561DC86BBDB82871254881A3575E5AEC9FB50389271F')
)) {
    if ((Get-FileHash -LiteralPath (Join-Path $CommonLib $fingerprint[0]) -Algorithm SHA256).Hash -ne $fingerprint[1]) {
        throw "CommonLib source fingerprint mismatch: $($fingerprint[0])"
    }
}
New-Item -ItemType Directory -Path $browserOutput -Force | Out-Null
$browserPreviousCommonLib = $env:OPENMCM_COMMONLIBSSE_NG
$browserPreviousVersion = $env:OPENMCM_BROWSER_VERSION
$env:OPENMCM_COMMONLIBSSE_NG = [IO.Path]::GetFullPath($CommonLib)
$env:OPENMCM_BROWSER_VERSION = $Version
Push-Location $browserRoot
try {
    # Keep xmake's generated build tree in the workspace; nothing is installed.
    & $Xmake f -P $browserSource -p windows -a x64 -m release -y | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw 'Browser native configuration failed.' }
    foreach ($browserTarget in @('OpenMCMBrowser', 'BrowserNativeTests', 'ProfileCodecTests')) {
        & $Xmake build -P $browserSource -y -j 8 $browserTarget | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw "Browser native build failed: $browserTarget" }
    }
    $browserGenerated = Join-Path $browserRoot 'build\windows\x64\release'
    foreach ($browserTest in @('BrowserNativeTests', 'ProfileCodecTests')) {
        & (Join-Path $browserGenerated ($browserTest + '.exe')) | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw "Browser native tests failed: $browserTest" }
    }
    $browserDll = Join-Path $browserOutput 'OpenMCMBrowser.dll'
    Copy-Item -LiteralPath (Join-Path $browserGenerated 'OpenMCMBrowser.dll') -Destination $browserDll -Force
    & $Python (Join-Path $browserRoot 'tools\check_browser_native.py') $browserDll | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { throw 'Browser native DLL artifact check failed.' }
    $browserSourceArchive = ''
    if (-not $SkipSourceArchive) {
        $browserSourceArchive = Join-Path $browserOutput ("OpenMCMBrowser-$Version-Source.zip")
        & $Python (Join-Path $browserRoot 'tools\package_browser_native_source.py') --project-root $browserRoot --commonlib $CommonLib --output $browserSourceArchive | ForEach-Object { Write-Host $_ }
        if ($LASTEXITCODE -ne 0) { throw 'Browser corresponding-source archive creation failed.' }
    }
}
finally {
    Pop-Location
    $env:OPENMCM_COMMONLIBSSE_NG = $browserPreviousCommonLib
    $env:OPENMCM_BROWSER_VERSION = $browserPreviousVersion
}
[pscustomobject]@{
    DllPath = $browserDll
    Sha256 = (Get-FileHash -LiteralPath $browserDll -Algorithm SHA256).Hash
    SupportedGameRuntimes = @('1.5.97', '1.6.640', '1.6.1170', '1.7.104')
    AddressLibraryRequired = $true
    GameTested = $false
    SourceArchivePath = $browserSourceArchive
}
