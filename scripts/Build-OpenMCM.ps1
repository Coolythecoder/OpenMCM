[CmdletBinding()]
param(
    [string] $SkyrimPath,
    [Parameter(Mandatory)]
    [ValidatePattern('^[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?$')]
    [string] $Version,
    [ValidateSet('Fomod', 'Standalone')]
    [string] $PackageFormat = 'Fomod',
    [switch] $SkipTests
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$toolsRoot = Join-Path $projectRoot '.tools'
$buildRoot = Join-Path $projectRoot 'build'
$workRoot = Join-Path $buildRoot 'work'
$stagingRoot = Join-Path $buildRoot 'staging'
$dataRoot = Join-Path $stagingRoot 'Data'
$distRoot = Join-Path $projectRoot 'dist'
$archiveSuffix = if ($PackageFormat -eq 'Fomod') { '-FOMOD' } else { '' }
$archivePath = [IO.Path]::GetFullPath((Join-Path $distRoot "OpenMCM-$Version$archiveSuffix.zip"))
$distPrefix = [IO.Path]::GetFullPath($distRoot).TrimEnd('\') + '\'
if (-not $archivePath.StartsWith($distPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to write an archive outside '$distRoot': $archivePath"
}
# Published archives can contain owner-maintained compliance edits. Refuse the
# destination before downloading tools or replacing any build staging folders.
if (Test-Path -LiteralPath $archivePath) {
    throw "Refusing to overwrite an existing release archive: $archivePath"
}

function Assert-LastExitCode {
    param([Parameter(Mandatory)] [string] $Operation)
    if ($LASTEXITCODE -ne 0) {
        throw "$Operation failed with exit code $LASTEXITCODE."
    }
}

function Convert-CapricaSkyUIIdentifiers {
    param([Parameter(Mandatory)] [string] $Path)

    # Caprica 0.3 lowercases the first character of referenced custom Papyrus
    # types, including SKI_ConfigBase[] and the opt-in OpenMCM_ConfigBase.
    # Repair complete string-table symbols only, not source/debug metadata or
    # arbitrary bytecode/literal substrings. The first-byte replacement keeps
    # every PEX offset, string length and string index unchanged.
    $repairCount = 0
    foreach ($pex in Get-ChildItem -LiteralPath $Path -Filter '*.pex' -File) {
        $bytes = [IO.File]::ReadAllBytes($pex.FullName)
        if ($bytes.Length -lt 16 -or
            [BitConverter]::ToString($bytes, 0, 8) -cne 'FA-57-C0-DE-03-02-00-01') {
            throw "Expected a Skyrim PEX 3.2/1 file: $($pex.FullName)"
        }
        $offset = 16 # magic, version/game and compilation timestamp
        # Source path, compiler user and machine are not type references.
        for ($metadataIndex = 0; $metadataIndex -lt 3; $metadataIndex++) {
            if ($offset + 2 -gt $bytes.Length) { throw "Truncated PEX metadata: $($pex.Name)" }
            $length = ([int]$bytes[$offset] -shl 8) -bor [int]$bytes[$offset + 1]
            $offset += 2
            if ($offset + $length -gt $bytes.Length) { throw "Truncated PEX metadata: $($pex.Name)" }
            $offset += $length
        }
        if ($offset + 2 -gt $bytes.Length) { throw "Truncated PEX string table: $($pex.Name)" }
        $stringCount = ([int]$bytes[$offset] -shl 8) -bor [int]$bytes[$offset + 1]
        $offset += 2
        $changed = $false
        for ($stringIndex = 0; $stringIndex -lt $stringCount; $stringIndex++) {
            if ($offset + 2 -gt $bytes.Length) { throw "Truncated PEX string table: $($pex.Name)" }
            $length = ([int]$bytes[$offset] -shl 8) -bor [int]$bytes[$offset + 1]
            $offset += 2
            if ($offset + $length -gt $bytes.Length) { throw "Truncated PEX string: $($pex.Name)" }
            $symbol = [Text.UTF8Encoding]::new($false, $true).GetString($bytes, $offset, $length)
            if ($symbol -cmatch '^sKI_[A-Za-z0-9_]+(?:\[\])?$') {
                $bytes[$offset] = 0x53
                $changed = $true
                $repairCount += 1
            }
            elseif ($symbol -cmatch '^openMCM(?:_[A-Za-z0-9_]+)?(?:\[\])?$') {
                $bytes[$offset] = 0x4F
                $changed = $true
                $repairCount += 1
            }
            elseif ($symbol -ceq 'stringUtil') {
                $bytes[$offset] = 0x53
                $changed = $true
                $repairCount += 1
            }
            $offset += $length
        }
        if ($changed) {
            [IO.File]::WriteAllBytes($pex.FullName, $bytes)
        }
    }

    return $repairCount
}

function Reset-BuildDirectory {
    param([Parameter(Mandatory)] [string] $Path)
    $resolved = [IO.Path]::GetFullPath($Path)
    $buildPrefix = [IO.Path]::GetFullPath($buildRoot).TrimEnd('\') + '\'
    if (-not $resolved.StartsWith($buildPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to reset a directory outside '$buildRoot': $resolved"
    }
    if (Test-Path -LiteralPath $resolved) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
    New-Item -ItemType Directory -Path $resolved -Force | Out-Null
}

function Reset-ToolDirectory {
    param([Parameter(Mandatory)] [string] $Path)
    $resolved = [IO.Path]::GetFullPath($Path)
    $toolsPrefix = [IO.Path]::GetFullPath($toolsRoot).TrimEnd('\') + '\'
    if (-not $resolved.StartsWith($toolsPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to reset a directory outside '$toolsRoot': $resolved"
    }
    if (Test-Path -LiteralPath $resolved) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
    New-Item -ItemType Directory -Path $resolved -Force | Out-Null
}

function Get-VerifiedDownload {
    param(
        [Parameter(Mandatory)] [string] $Uri,
        [Parameter(Mandatory)] [string] $Destination,
        [Parameter(Mandatory)] [string] $Sha256,
        [string] $UserAgent = 'OpenMCM reproducible build'
    )

    $destinationDirectory = Split-Path -Parent $Destination
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null

    if (Test-Path -LiteralPath $Destination -PathType Leaf) {
        $actual = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
        if ($actual -eq $Sha256) {
            return
        }
        Remove-Item -LiteralPath $Destination -Force
    }

    Write-Host "Downloading $([IO.Path]::GetFileName($Destination))..."
    Invoke-WebRequest -UseBasicParsing -Uri $Uri -OutFile $Destination `
        -Headers @{ 'User-Agent' = $UserAgent } -MaximumRedirection 10
    $actual = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash
    if ($actual -ne $Sha256) {
        Remove-Item -LiteralPath $Destination -Force
        throw "Checksum mismatch for '$Uri'. Expected $Sha256, received $actual."
    }
}

function Find-SkyrimInstallation {
    param([string] $RequestedPath)

    $candidates = [Collections.Generic.List[string]]::new()
    if ($RequestedPath) {
        $candidates.Add($RequestedPath)
    }

    $appPathKey = 'Registry::HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\SkyrimSE.exe'
    if (Test-Path $appPathKey) {
        $exePath = (Get-ItemProperty -Path $appPathKey -ErrorAction SilentlyContinue).'(default)'
        if ($exePath) {
            $candidates.Add((Split-Path -Parent $exePath))
        }
    }

    $steamRoots = @(
        (Join-Path ${env:ProgramFiles(x86)} 'Steam'),
        (Join-Path $env:ProgramFiles 'Steam')
    ) | Where-Object { $_ -and (Test-Path -LiteralPath $_) }

    foreach ($steamRoot in $steamRoots) {
        $candidates.Add((Join-Path $steamRoot 'steamapps\common\Skyrim Special Edition'))
        $libraryFile = Join-Path $steamRoot 'steamapps\libraryfolders.vdf'
        if (Test-Path -LiteralPath $libraryFile -PathType Leaf) {
            $vdf = Get-Content -LiteralPath $libraryFile -Raw
            foreach ($match in [regex]::Matches($vdf, '"path"\s+"([^"]+)"')) {
                $libraryRoot = $match.Groups[1].Value.Replace('\\', '\')
                # Join-Path rejects stale library entries whose drive is no
                # longer mounted. Path.Combine lets the validation loop below
                # skip them normally.
                $candidates.Add([IO.Path]::Combine(
                    $libraryRoot, 'steamapps\common\Skyrim Special Edition'))
            }
        }
    }

    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        $candidatePath = $candidate
        if ([IO.Path]::GetFileName($candidatePath) -ieq 'SkyrimSE.exe') {
            $candidatePath = Split-Path -Parent $candidatePath
        }
        $full = [IO.Path]::GetFullPath($candidatePath)
		if ((Test-Path -LiteralPath ([IO.Path]::Combine($full, 'SkyrimSE.exe')) -PathType Leaf) -and
			(Test-Path -LiteralPath ([IO.Path]::Combine($full, 'Data', 'Skyrim - Interface.bsa')) -PathType Leaf)) {
            return $full
        }
    }

    throw 'Skyrim Special Edition was not found. Pass -SkyrimPath or set SKYRIM_SE_PATH.'
}

function Initialize-BuildTools {
    New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null
    $downloadRoot = Join-Path $toolsRoot 'downloads'
    New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null

    $bsarch = Join-Path $toolsRoot 'bsarch.exe'
    Get-VerifiedDownload `
        -Uri 'https://raw.githubusercontent.com/TES5Edit/TES5Edit/b3235062f275a7d4a94162af910923ba79f0e77a/Tools/BSArchive/bsarch.exe' `
        -Destination $bsarch `
        -Sha256 '2633633E9566CF765CAA0267D45F6C87733366206144A9743387E0562D694FED'

    $capricaDirectory = Join-Path $toolsRoot 'caprica-0.3.0'
    $capricaArchive = Join-Path $downloadRoot 'Caprica.v0.3.0.7z'
    $caprica = Join-Path $capricaDirectory 'Caprica.exe'
    Get-VerifiedDownload `
        -Uri 'https://github.com/Orvid/Caprica/releases/download/v0.3.0/Caprica.v0.3.0.7z' `
        -Destination $capricaArchive `
        -Sha256 '0037E54CF3A1021E976278D9A637E8AE541AAF9EBEB8D274B6C2CFE32F4EE559'
    Reset-ToolDirectory -Path $capricaDirectory
    & $tar.Source -xf $capricaArchive -C $capricaDirectory
    Assert-LastExitCode 'Extracting Caprica'

    $ffdecDirectory = Join-Path $toolsRoot 'ffdec-26.2.1'
    $ffdecArchive = Join-Path $downloadRoot 'ffdec_26.2.1.zip'
    $ffdec = Join-Path $ffdecDirectory 'ffdec-cli.exe'
    Get-VerifiedDownload `
        -Uri 'https://github.com/jindrapetrik/jpexs-decompiler/releases/download/version26.2.1/ffdec_26.2.1.zip' `
        -Destination $ffdecArchive `
        -Sha256 '0333B56998A55BD83F4E0DEB678A811FCDC45607582B4F5DD438309C8C3AD5CE'
    Reset-ToolDirectory -Path $ffdecDirectory
    Expand-Archive -LiteralPath $ffdecArchive -DestinationPath $ffdecDirectory -Force

    $mtascDirectory = Join-Path $toolsRoot 'mtasc-1.15'
    $mtascArchive = Join-Path $downloadRoot 'mtasc-1.15-win.zip'
    $mtasc = Join-Path $mtascDirectory 'mtasc.exe'
    Get-VerifiedDownload `
        -Uri 'https://sourceforge.net/projects/mtasc/files/mtasc-1.15-win.zip/download' `
        -Destination $mtascArchive `
        -Sha256 '97094F110862B958BD146439808E8EEE08BE73C433C1C76916759624F59ED2A1' `
        -UserAgent 'Wget/1.21.4'
    Reset-ToolDirectory -Path $mtascDirectory
    Expand-Archive -LiteralPath $mtascArchive -DestinationPath $mtascDirectory -Force

    $spriggitDirectory = Join-Path $toolsRoot 'spriggit-0.41.0'
    $spriggitArchive = Join-Path $downloadRoot 'SpriggitCLI.zip'
    $spriggit = Join-Path $spriggitDirectory 'Spriggit.CLI.exe'
    Get-VerifiedDownload `
        -Uri 'https://github.com/Mutagen-Modding/Spriggit/releases/download/0.41.0/SpriggitCLI.zip' `
        -Destination $spriggitArchive `
        -Sha256 '9B1088EED09F3B6B9D30A40B3B0545CEA4C84C3F821B512590A60819F6916529'
    Reset-ToolDirectory -Path $spriggitDirectory
    Expand-Archive -LiteralPath $spriggitArchive -DestinationPath $spriggitDirectory -Force

    foreach ($tool in @($bsarch, $caprica, $ffdec, $mtasc, $spriggit)) {
        if (-not (Test-Path -LiteralPath $tool -PathType Leaf)) {
            throw "Build tool was not prepared correctly: $tool"
        }
    }

    return @{
        BSArch = $bsarch
        Caprica = $caprica
        FFDec = $ffdec
        MTASC = $mtasc
        Spriggit = $spriggit
    }
}

$java = Get-Command java -ErrorAction SilentlyContinue
if (-not $java) {
    throw 'Java was not found on PATH. Install a 64-bit Java runtime (8 or newer) for FFDec.'
}
& $java.Source -version *> $null
Assert-LastExitCode 'Checking Java'

$tar = Get-Command tar.exe -ErrorAction SilentlyContinue
if (-not $tar) {
    throw 'tar.exe was not found on PATH. OpenMCM requires the tar tool included with supported Windows releases.'
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw 'Python 3.10+ is required for Papyrus metadata normalization, package assembly and tests, including -SkipTests builds.'
}
& $python.Source -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
if ($LASTEXITCODE -ne 0) {
    throw 'OpenMCM builds require Python 3.10 or newer.'
}

$gameRoot = Find-SkyrimInstallation -RequestedPath $SkyrimPath
$gameExe = Join-Path $gameRoot 'SkyrimSE.exe'
$interfaceBsa = Join-Path $gameRoot 'Data\Skyrim - Interface.bsa'
$gameVersion = (Get-Item -LiteralPath $gameExe).VersionInfo.ProductVersion
Write-Host "Building OpenMCM $Version from Skyrim SE $gameVersion at '$gameRoot'."

$tool = Initialize-BuildTools
Reset-BuildDirectory -Path $workRoot
Reset-BuildDirectory -Path $stagingRoot
New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null

# This separate native component does not host the MCM. Its narrowly scoped
# engine patch is runtime- and byte-guarded; the Papyrus/Scaleform host remains
# usable without it. Native safety tests run even when Python tests are skipped.
$nativeRuntime = & (Join-Path $PSScriptRoot 'Build-NativeRuntime.ps1') `
    -ProjectRoot $projectRoot -Version $Version
$nativeInstallRoot = Join-Path $dataRoot 'SKSE\Plugins'
New-Item -ItemType Directory -Path $nativeInstallRoot -Force | Out-Null
Copy-Item -LiteralPath $nativeRuntime.DllPath -Destination $nativeInstallRoot
Copy-Item -LiteralPath $nativeRuntime.IniPath -Destination $nativeInstallRoot
foreach ($nativeFile in @('OpenMCMRuntime.dll', 'OpenMCMRuntime.ini')) {
    if (-not (Test-Path -LiteralPath (Join-Path $nativeInstallRoot $nativeFile) -PathType Leaf)) {
        throw "Native runtime package output is missing: $nativeFile"
    }
}

# Persistence-only GPL component adapted from Redone's original native code.
# It is a separate optional FOMOD choice; save-local browser state needs no DLL.
$browserNative = & (Join-Path $PSScriptRoot 'Build-BrowserNative.ps1') `
    -ProjectRoot $projectRoot -Version $Version
Copy-Item -LiteralPath $browserNative.DllPath -Destination $nativeInstallRoot

# Build the exact compatibility plugin identity required by MCM Helper.
$isolatedAppData = Join-Path $toolsRoot 'spriggit-appdata'
$nugetDirectory = Join-Path $isolatedAppData 'NuGet'
New-Item -ItemType Directory -Path $nugetDirectory -Force | Out-Null
$nugetConfig = @'
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <clear />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" protocolVersion="3" />
  </packageSources>
</configuration>
'@
[IO.File]::WriteAllText((Join-Path $nugetDirectory 'NuGet.Config'), $nugetConfig,
    [Text.UTF8Encoding]::new($false))

$previousAppData = $env:APPDATA
try {
    $env:APPDATA = $isolatedAppData
    & $tool.Spriggit deserialize `
        -i (Join-Path $projectRoot 'src\plugin\SkyUI_SE.esp') `
        -o (Join-Path $dataRoot 'SkyUI_SE.esp') `
        -p 'Spriggit.Yaml.Skyrim' -v '0.41.0'
    Assert-LastExitCode 'Building SkyUI_SE.esp compatibility plugin'
}
finally {
    $env:APPDATA = $previousAppData
}

# Explicitly sequence both start-enabled quests. Skyrim can otherwise defer a
# newly added quest until a save/reload cycle, which leaves the MCM page alive
# but with no manager listening on an existing save. Form IDs in SEQ files use
# their on-disk master index; SkyUI_SE.esp has one master, so its local 0x802 and
# 0x830 records are encoded as 0x01000802 and 0x01000830. Local 0x820 is
# retained as an inactive compatibility tombstone for saves that used SkyUI's
# persistent built-in config quest.
$sequenceDirectory = Join-Path $dataRoot 'Seq'
New-Item -ItemType Directory -Path $sequenceDirectory -Force | Out-Null
$sequencePath = Join-Path $sequenceDirectory 'SkyUI_SE.seq'
$sequenceBytes = [byte[]]@(
	0x02, 0x08, 0x00, 0x01,
	0x30, 0x08, 0x00, 0x01
)
[IO.File]::WriteAllBytes($sequencePath, $sequenceBytes)
$writtenSequence = [IO.File]::ReadAllBytes($sequencePath)
if ([Convert]::ToBase64String($writtenSequence) -ne
    [Convert]::ToBase64String($sequenceBytes)) {
    throw "Generated startup sequence '$sequencePath' failed verification."
}

# Compile clean-room SkyUI-compatible Papyrus scripts. Stubs are compile-time only.
$compiledScripts = Join-Path $dataRoot 'Scripts'
New-Item -ItemType Directory -Path $compiledScripts -Force | Out-Null
$papyrusSource = Join-Path $projectRoot 'src\papyrus'
$papyrusStubs = Join-Path $projectRoot 'vendor\papyrus-stubs'
$papyrusFlags = Join-Path $papyrusStubs 'TESV_Papyrus_Flags.flg'
& $tool.Caprica --game=skyrim `
    "--output=$compiledScripts" `
    "--import=$papyrusSource" `
    "--import=$papyrusStubs" `
    "--flags=$papyrusFlags" `
    --parallel-compile --release --final `
    --skyrim-allow-unknown-events-on-non-native-class=true `
    $papyrusSource
Assert-LastExitCode 'Compiling Papyrus scripts'

& $python.Source -B (Join-Path $projectRoot 'tools\sanitize_papyrus_metadata.py') $compiledScripts
Assert-LastExitCode 'Normalizing generated Papyrus compiler metadata'
$identifierRepairCount = Convert-CapricaSkyUIIdentifiers -Path $compiledScripts
$managerPex = Join-Path $compiledScripts 'SKI_ConfigManager.pex'
$managerPexText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($managerPex))
if (-not $managerPexText.Contains('SKI_ConfigBase[]')) {
    throw 'Compiled SKI_ConfigManager.pex does not contain the exact SKI_ConfigBase[] registry type.'
}
foreach ($pex in Get-ChildItem -LiteralPath $compiledScripts -Filter '*.pex' -File) {
    $pexText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($pex.FullName))
    if ($pexText.Contains('sKI_')) {
        throw "Compiled Papyrus script '$($pex.Name)' still contains a case-corrupted sKI_ type reference."
    }
    if ($pexText.Contains('openMCM_ConfigBase') -or $pexText.Contains('openMCM_ConfigMenu')) {
        throw "Compiled Papyrus script '$($pex.Name)' still contains a case-corrupted OpenMCM type reference."
    }
}
Write-Host "Canonicalized $identifierRepairCount Caprica custom-type reference(s)."

$sourceInstall = Join-Path $dataRoot 'Source\Scripts'
New-Item -ItemType Directory -Path $sourceInstall -Force | Out-Null
Copy-Item -Path (Join-Path $projectRoot 'src\papyrus\*.psc') -Destination $sourceInstall

# Compile both the traditional and opt-in SDK examples as build-time tests.
# Their sources ship as documentation; neither example PEX is installed.
$exampleSources = @(
    (Join-Path $projectRoot 'examples\OpenMCMExample.psc'),
    (Join-Path $projectRoot 'examples\OpenMCMApiExample.psc')
)
$exampleOutput = Join-Path $workRoot 'example-compile'
New-Item -ItemType Directory -Path $exampleOutput -Force | Out-Null
foreach ($exampleSource in $exampleSources) {
    Push-Location (Split-Path -Parent $exampleSource)
    try {
        & $tool.Caprica --game=skyrim `
            "--output=$exampleOutput" `
            "--import=$papyrusSource" `
            "--import=$papyrusStubs" `
            "--flags=$papyrusFlags" `
            --release --final `
            --skyrim-allow-unknown-events-on-non-native-class=true `
            $exampleSource
        Assert-LastExitCode "Compiling example $([IO.Path]::GetFileName($exampleSource))"
    }
    finally { Pop-Location }
}
& $python.Source -B (Join-Path $projectRoot 'tools\sanitize_papyrus_metadata.py') $exampleOutput
Assert-LastExitCode 'Normalizing generated example compiler metadata'
$exampleIdentifierRepairs = Convert-CapricaSkyUIIdentifiers -Path $exampleOutput
$apiExamplePex = Join-Path $exampleOutput 'OpenMCMApiExample.pex'
if (-not (Test-Path -LiteralPath $apiExamplePex -PathType Leaf)) {
    throw 'Opt-in API example compilation did not produce OpenMCMApiExample.pex.'
}
$apiExampleText = [Text.Encoding]::ASCII.GetString([IO.File]::ReadAllBytes($apiExamplePex))
if (-not $apiExampleText.Contains('OpenMCM_ConfigBase') -or $apiExampleText.Contains('openMCM_ConfigBase')) {
    throw 'Opt-in API example PEX must reference canonical OpenMCM_ConfigBase.'
}
Write-Host "Canonicalized $exampleIdentifierRepairs SDK-example custom-type reference(s)."

# Derive the Journal menu from the user's vanilla BSA; no Bethesda asset is kept in source.
$vanillaRoot = Join-Path $workRoot 'vanilla-interface'
New-Item -ItemType Directory -Path $vanillaRoot -Force | Out-Null
& $tool.BSArch unpack $interfaceBsa $vanillaRoot -quiet
Assert-LastExitCode 'Extracting Skyrim - Interface.bsa'
$vanillaJournal = Join-Path $vanillaRoot 'interface\quest_journal.swf'
if (-not (Test-Path -LiteralPath $vanillaJournal -PathType Leaf)) {
    throw "BSArch did not extract '$vanillaJournal'."
}

$swfRoot = Join-Path $workRoot 'journal'
$exportRoot = Join-Path $swfRoot 'exported'
$hostImport = Join-Path $swfRoot 'host-import\__Packages'
$hostPatchedSwf = Join-Path $swfRoot 'quest_journal_host.swf'
$finalSwf = Join-Path $dataRoot 'Interface\quest_journal.swf'
New-Item -ItemType Directory -Path $exportRoot,$hostImport,(Split-Path -Parent $finalSwf) -Force | Out-Null
Copy-Item -LiteralPath $vanillaJournal -Destination $hostPatchedSwf

& $tool.FFDec -config autoDeobfuscate=false -onerror abort `
    -export script $exportRoot $hostPatchedSwf *> (Join-Path $swfRoot 'ffdec-export.log')
Assert-LastExitCode 'Exporting vanilla Journal ActionScript'

& (Join-Path $projectRoot 'scripts\Patch-Journal.ps1') `
    -ExportedScriptsPath (Join-Path $exportRoot 'scripts')

Copy-Item -LiteralPath (Join-Path $exportRoot 'scripts\__Packages\Quest_Journal.as') `
    -Destination (Join-Path $hostImport 'Quest_Journal.as')
Copy-Item -LiteralPath (Join-Path $exportRoot 'scripts\__Packages\SystemPage.as') `
    -Destination (Join-Path $hostImport 'SystemPage.as')

& $tool.FFDec -config autoDeobfuscate=false,decompile=false -onerror abort `
    -importScript $hostPatchedSwf $hostPatchedSwf (Split-Path -Parent $hostImport) `
    *> (Join-Path $swfRoot 'ffdec-import.log')
Assert-LastExitCode 'Compiling Journal host patches'

# FFDec replaces existing AS2 classes; MTASC is required to add our new classes.
& $tool.MTASC -version 8 `
    -cp (Join-Path $projectRoot 'src\actionscript') `
    -swf $hostPatchedSwf -out $finalSwf -keep -main `
    (Join-Path $projectRoot 'src\actionscript\MCMCompatEntry.as') `
    (Join-Path $projectRoot 'src\actionscript\ConfigPanel.as') `
    *> (Join-Path $swfRoot 'mtasc.log')
Assert-LastExitCode 'Embedding OpenMCM ActionScript classes'

# Generate an English fallback table for every language identifier shipped by
# SkyUI. Mods continue to provide their own localized option strings.
$translationDirectory = Join-Path $dataRoot 'Interface\Translations'
New-Item -ItemType Directory -Path $translationDirectory -Force | Out-Null
$translationSource = Get-Content -LiteralPath `
    (Join-Path $projectRoot 'src\translations\SkyUI_SE_ENGLISH.tsv') -Raw
$translationLanguages = @(
    'CHINESE', 'CZECH', 'ENGLISH', 'FRENCH', 'GERMAN',
    'ITALIAN', 'JAPANESE', 'POLISH', 'RUSSIAN', 'SPANISH'
)
foreach ($language in $translationLanguages) {
    [IO.File]::WriteAllText(
        (Join-Path $translationDirectory "SkyUI_SE_$language.txt"),
        $translationSource,
        [Text.Encoding]::Unicode)
}

# Verify the final SWF has both patched hosts and genuinely embedded new classes.
$verifyRoot = Join-Path $swfRoot 'verify'
New-Item -ItemType Directory -Path $verifyRoot -Force | Out-Null
& $tool.FFDec -config autoDeobfuscate=false -onerror abort `
    -export script $verifyRoot $finalSwf *> (Join-Path $swfRoot 'ffdec-verify.log')
Assert-LastExitCode 'Round-trip exporting the final Journal SWF'

$requiredAs2Files = @(
    'ConfigPanel.as',
    'MCMCompatBootstrap.as',
    'MCMCompatEntry.as',
    'MCMCompatList.as',
    'MCMCompatPanel.as',
    'MCMCompatBrowser.as',
    'MCMCompatExtensions.as',
    'MCMCompatUtil.as',
    'gfx\managers\FocusHandler.as',
    'Quest_Journal.as',
    'SystemPage.as'
)
$verifyPackages = Join-Path $verifyRoot 'scripts\__Packages'
foreach ($name in $requiredAs2Files) {
    if (-not (Test-Path -LiteralPath (Join-Path $verifyPackages $name) -PathType Leaf)) {
        throw "Final SWF is missing embedded AS2 class '$name'."
    }
}

$classTokenRequirements = [ordered]@{
    'Quest_Journal.as' = @(
        'MCMCompatBootstrap.install', 'function ConfigPanelOpen()',
        'function ConfigPanelClose()'
    )
    'SystemPage.as' = @('$MOD CONFIGURATION', 'ConfigPanelOpen')
    'MCMCompatBootstrap.as' = @('ConfigPanelFader', 'configPanel', 'rootPath')
    'MCMCompatEntry.as' = @('MCMCompatBootstrap.install')
    'MCMCompatList.as' = @(
        'function getRenderer(', 'function getRendererForIndex(',
        'function beginUpdate()', 'function endUpdate()',
        'function refreshMouseSelection()', 'function pressIndex(',
        'disableInput', 'disableSelection', 'isListAnimating',
        '.onRollOver = function()', '.onRollOut = function()',
        '.onPress = function(', 'this._list.pressIndex(this.itemIndex,',
        'this._event("itemPress",this._selectedIndex,',
        'this.onItemPress.call(this.owner,'
    )
    'MCMCompatPanel.as' = @(
        'SKICP_modSelected', 'SKICP_inputAccepted', 'flushOptionBuffers',
        'handleInput', 'EndRemapMode', 'activeIndex',
        '_beginModListRequest', '_modListRequestAttempts',
        'Stage.scaleMode = "showAll"', '_onListPress', '_onMenuPress',
        '_modList', '_pageList', '_optionsList', '_menuDialogList',
        'triggerArea', '_textInputOwned', '_setTextInputEnabled',
        '_syncListInput', '_acquireDialogFocus', '_restoreDialogFocus',
        '_focusComponent', '_focusActiveList'
    )
    'MCMCompatUtil.as' = @(
        'sendModEvent', 'startRemapMode', 'drawHorizontalGradientRect',
        'beginGradientFill', 'allowTextInput', 'function applyHtmlText('
    )
    'gfx\managers\FocusHandler.as' = @(
        'Selection.disableFocusRolloverEvent = true',
        'Selection.disableFocusAutoRelease = true',
        'currentFocusLookup', 'actualFocusLookup',
        'function getFocus(', 'function setFocus('
    )
    'ConfigPanel.as' = @('ABI_METHODS', 'handleInput', 'EndRemapMode')
}
foreach ($className in $classTokenRequirements.Keys) {
    $classText = Get-Content -LiteralPath (Join-Path $verifyPackages $className) -Raw
    foreach ($token in $classTokenRequirements[$className]) {
        if (-not $classText.Contains($token)) {
            throw "Final SWF class '$className' is missing verification token '$token'."
        }
    }
}

$panelClassText = Get-Content -LiteralPath (Join-Path $verifyPackages 'MCMCompatPanel.as') -Raw
$listClassText = Get-Content -LiteralPath (Join-Path $verifyPackages 'MCMCompatList.as') -Raw
$utilClassText = Get-Content -LiteralPath (Join-Path $verifyPackages 'MCMCompatUtil.as') -Raw
$htmlMethod = [regex]::Match($utilClassText,
    'function applyHtmlText\([^)]*\)\s*\{(?<body>.*?)\r?\n   \}',
    [Text.RegularExpressions.RegexOptions]::Singleline)
if (-not $htmlMethod.Success) { throw 'Final SWF is missing HTML text formatting.' }
$htmlBody = $htmlMethod.Groups['body'].Value
$htmlAssignment = $htmlBody.IndexOf('field.htmlText =')
$parsedReadback = $htmlBody.IndexOf('field.getTextFormat()')
$currentFormat = $htmlBody.IndexOf('field.setTextFormat(')
$futureFormat = $htmlBody.IndexOf('field.setNewTextFormat(')
if ($htmlAssignment -lt 0 -or $parsedReadback -le $htmlAssignment -or
    $currentFormat -le $parsedReadback -or $futureFormat -le $currentFormat -or
    $htmlBody.Contains('new TextFormat(')) {
    throw 'Final SWF HTML text must preserve parsed fonts/colors before restoring future defaults.'
}
foreach ($token in @('MCMCompatUtil.translate(value)', 'MCMCompatUtil.applyText(field,',
    '.indexOf("<")', '.indexOf("&")', '<font face=', '<p align=',
    'MCMCompatUtil.hexColor(', 'MCMCompatUtil.escapeHtmlAttribute(')) {
    if (-not $htmlBody.Contains($token)) {
        throw "Final SWF text helper is missing explicit-default/plain-path token '$token'."
    }
}
if ($listClassText.Contains('.onRelease = function(')) {
    throw 'Final SWF pooled list renderers must dispatch on press, not release.'
}
foreach ($rejected in @('suspendJournalInput', 'restoreJournalInput', '_journalInputState',
    '_addModalInputBlocker')) {
    foreach ($className in @('MCMCompatPanel.as', 'MCMCompatBootstrap.as', 'Quest_Journal.as')) {
        $classText = Get-Content -LiteralPath (Join-Path $verifyPackages $className) -Raw
        if ($classText.Contains($rejected)) {
            throw "Final SWF '$className' still contains the rejected input workaround '$rejected'."
        }
    }
}

function Assert-VisibleTransparentTrigger {
    param([string] $Text, [string] $Description)
    # FFDec renames locals, but preserves the target across the opaque shape,
    # child alpha-zero transform, and visibility assignment. This reproduces
    # SkyUI's authored trigger without assigning a hidden replacement hitArea.
    $transparentTrigger = 'MCMCompatUtil\.drawRect\((?<trigger>_loc\d+_),[^;\r\n]+,0,100,0,0\);\s*\k<trigger>\._alpha = 0;\s*\k<trigger>\._visible = true;'
    if ($Text -notmatch $transparentTrigger -or $Text.Contains('.hitArea =')) {
        throw "Final SWF $Description must use a visible alpha-zero trigger, not a replacement hitArea."
    }
}
$renderSideIndex = $panelClassText.IndexOf('function _renderSide(')
$renderOptionsIndex = $panelClassText.IndexOf('function _renderOptions(', $renderSideIndex + 1)
if ($renderSideIndex -lt 0 -or $renderOptionsIndex -le $renderSideIndex) {
    throw 'Final SWF MCMCompatPanel is missing the expected side-list render methods.'
}
$renderSideText = $panelClassText.Substring(
    $renderSideIndex, $renderOptionsIndex - $renderSideIndex)
foreach ($token in @(
    'createEmptyMovieClip("triggerArea",0)', '.getRenderer(',
    '.beginUpdate()', '.endUpdate()', 'drawHorizontalGradientRect'
)) {
    if (-not $renderSideText.Contains($token)) {
        throw "Final SWF side list is missing mouse/geometry token '$token'."
    }
}
Assert-VisibleTransparentTrigger -Text $renderSideText -Description 'side list'
if ($renderSideText.Contains('._pressSide(') -or $renderSideText.Contains('this._sideRows.removeMovieClip()')) {
    throw 'Final SWF side list must keep its pooled renderers and dispatch through MCMCompatList.'
}
if ($renderSideText.Contains('.onRelease = function()')) {
    throw 'Final SWF side list still activates on release and can lose clicks after rollover.'
}

$drawOptionGlyphIndex = $panelClassText.IndexOf(
    'function _drawOptionGlyph(', $renderOptionsIndex + 1)
if ($drawOptionGlyphIndex -le $renderOptionsIndex) {
    throw 'Final SWF MCMCompatPanel is missing the expected options-list render boundary.'
}
$renderOptionsText = $panelClassText.Substring(
    $renderOptionsIndex, $drawOptionGlyphIndex - $renderOptionsIndex)
foreach ($token in @(
    'createEmptyMovieClip("triggerArea",0)', '.getRenderer(',
    '.beginUpdate()', '.endUpdate()'
)) {
    if (-not $renderOptionsText.Contains($token)) {
        throw "Final SWF options list is missing mouse token '$token'."
    }
}
Assert-VisibleTransparentTrigger -Text $renderOptionsText -Description 'options list'
if ($renderOptionsText.Contains('._pressOption(') -or $renderOptionsText.Contains('this._optionRows.removeMovieClip()')) {
    throw 'Final SWF options list must keep its pooled renderers and dispatch through MCMCompatList.'
}
if ($renderOptionsText.Contains('.onRelease = function()')) {
    throw 'Final SWF options list still activates on release.'
}

$renderMenuIndex = $panelClassText.IndexOf('function _renderMenuDialog(')
$renderColorIndex = $panelClassText.IndexOf(
    'function _renderColorDialog(', $renderMenuIndex + 1)
if ($renderMenuIndex -lt 0 -or $renderColorIndex -le $renderMenuIndex) {
    throw 'Final SWF MCMCompatPanel is missing the expected menu-dialog render methods.'
}
$renderMenuText = $panelClassText.Substring(
    $renderMenuIndex, $renderColorIndex - $renderMenuIndex)
foreach ($token in @(
    'createEmptyMovieClip("triggerArea",0)', 'this._menuDialogList.getRenderer(',
    '.beginUpdate()', '.endUpdate()', 'this._onMenuPress'
)) {
    if (-not $renderMenuText.Contains($token)) {
        throw "Final SWF menu dialog is missing mouse token '$token'."
    }
}
Assert-VisibleTransparentTrigger -Text $renderMenuText -Description 'menu dialog'
if ($renderMenuText.Contains('.onPress = function(')) {
    throw 'Final SWF menu dialog must use list-owned pooled row handlers.'
}
if ($renderMenuText.Contains('.onRelease = function()')) {
    throw 'Final SWF menu dialog still activates on release.'
}

$closeDialogIndex = $panelClassText.IndexOf('function _closeDialog(')
if ($closeDialogIndex -lt 0) {
    throw "Final SWF MCMCompatPanel is missing _closeDialog."
}
$closeDialogText = $panelClassText.Substring($closeDialogIndex)
foreach ($token in @('this._setContentDimmed(false)', 'this._restoreDialogFocus()')) {
    if (-not $closeDialogText.Contains($token)) {
        throw "Final SWF _closeDialog is missing focus-restoration token '$token'."
    }
}

$restoreFocusIndex = $panelClassText.IndexOf('function _restoreDialogFocus(')
$textInputIndex = $panelClassText.IndexOf('function _setTextInputEnabled(', $restoreFocusIndex + 1)
if ($restoreFocusIndex -lt 0 -or $textInputIndex -le $restoreFocusIndex) {
    throw 'Final SWF MCMCompatPanel is missing dialog-focus ownership restoration.'
}
$restoreFocusText = $panelClassText.Substring($restoreFocusIndex, $textInputIndex - $restoreFocusIndex)
foreach ($token in @('this._previousDialogFocus', 'this._dialogFocusOwned = false',
    '!this._active', 'this._focusComponent(', 'this._focusActiveList()')) {
    if (-not $restoreFocusText.Contains($token)) {
        throw "Final SWF saved-focus restoration is missing token '$token'."
    }
}

$adjustSliderIndex = $panelClassText.IndexOf('function _adjustSlider(')
$lockSliderIndex = $panelClassText.IndexOf('function _lockSliderValue(', $adjustSliderIndex + 1)
$mouseSliderIndex = $panelClassText.IndexOf('function _setSliderFromMouse(', $lockSliderIndex + 1)
if ($adjustSliderIndex -lt 0 -or $lockSliderIndex -le $adjustSliderIndex -or
    $mouseSliderIndex -le $lockSliderIndex) {
    throw "Final SWF MCMCompatPanel is missing the expected slider methods."
}
$adjustSliderText = $panelClassText.Substring($adjustSliderIndex,
    $lockSliderIndex - $adjustSliderIndex)
if (-not $adjustSliderText.Contains('this._lockSliderValue(')) {
    throw "Final SWF slider controls do not share the CLIK lockValue path."
}
$lockSliderText = $panelClassText.Substring($lockSliderIndex,
    $mouseSliderIndex - $lockSliderIndex)
$clampToken = 'Math.max(minimum,Math.min(maximum,raw))'
$roundToken = 'Math.round('
$intervalToken = '/ interval) * interval'
if (-not $lockSliderText.Contains($clampToken) -or
    -not $lockSliderText.Contains($roundToken) -or
    -not $lockSliderText.Contains($intervalToken) -or
    $lockSliderText.IndexOf($clampToken) -gt $lockSliderText.IndexOf($roundToken)) {
    throw "Final SWF _lockSliderValue does not implement CLIK clamp-then-zero-snap ordering."
}
if ($lockSliderText.Contains('- minimum')) {
    throw "Final SWF _lockSliderValue still snaps relative to the minimum instead of zero."
}

$verifyCorpus = ($requiredAs2Files | ForEach-Object {
    Get-Content -LiteralPath (Join-Path $verifyPackages $_) -Raw
}) -join "`n"
foreach ($token in @(
    'MCMCompatBootstrap.install',
    'ConfigPanelOpen',
    '$MOD CONFIGURATION',
    '_root.ConfigPanelFader.configPanel',
    'SKICP_modSelected',
    'SKICP_inputAccepted',
    '_beginModListRequest',
    'flushOptionBuffers'
)) {
    if (-not $verifyCorpus.Contains($token)) {
        throw "Final SWF verification token is missing: $token"
    }
}

if (-not $SkipTests) {
    & $python.Source -B (Join-Path $projectRoot 'tools\check_mcm_contract.py') `
        $projectRoot --profile source
    Assert-LastExitCode 'Running the source compatibility contract'
    & $python.Source -B (Join-Path $projectRoot 'tools\check_mcm_contract.py') `
        $stagingRoot --profile release
    Assert-LastExitCode 'Running the release compatibility contract'
    & $python.Source -B (Join-Path $projectRoot 'tools\check_openmcm_api.py') $stagingRoot
    Assert-LastExitCode 'Checking the staged opt-in OpenMCM API'
    & $python.Source -B (Join-Path $projectRoot 'tools\check_native_runtime.py') `
        $stagingRoot
    Assert-LastExitCode 'Checking the staged native runtime artifact'
    & $python.Source -B -m unittest discover `
        -s (Join-Path $projectRoot 'tests') -p 'test_*.py'
    Assert-LastExitCode 'Running unit tests'
}

Copy-Item -LiteralPath (Join-Path $projectRoot 'README.md') -Destination (Join-Path $stagingRoot 'README.md')
Copy-Item -LiteralPath (Join-Path $projectRoot 'README.txt') -Destination (Join-Path $stagingRoot 'README.txt')
Copy-Item -LiteralPath (Join-Path $projectRoot 'COMPATIBILITY.md') `
    -Destination (Join-Path $stagingRoot 'COMPATIBILITY.md')
$releaseNotesPath = Join-Path $projectRoot "release\OpenMCM-$Version-notes.md"
if (Test-Path -LiteralPath $releaseNotesPath -PathType Leaf) {
    Copy-Item -LiteralPath $releaseNotesPath -Destination (Join-Path $stagingRoot 'RELEASE_NOTES.md')
}
Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE') -Destination (Join-Path $stagingRoot 'LICENSE')
Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE.txt') -Destination (Join-Path $stagingRoot 'LICENSE.txt')
Copy-Item -LiteralPath (Join-Path $projectRoot 'licenses') `
    -Destination (Join-Path $stagingRoot 'licenses') -Recurse
Copy-Item -LiteralPath (Join-Path $projectRoot 'THIRD_PARTY_NOTICES.md') `
    -Destination (Join-Path $stagingRoot 'THIRD_PARTY_NOTICES.md')
Copy-Item -LiteralPath (Join-Path $projectRoot 'examples') `
    -Destination (Join-Path $stagingRoot 'examples') -Recurse
$sdkDocsRoot = Join-Path $stagingRoot 'docs'
New-Item -ItemType Directory -Path $sdkDocsRoot -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\OpenMCM-API.md') -Destination $sdkDocsRoot
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs\OpenMCM-Browser.md') -Destination $sdkDocsRoot
$correspondingSource = Join-Path $stagingRoot 'source'
New-Item -ItemType Directory -Path $correspondingSource -Force | Out-Null
Copy-Item -LiteralPath $browserNative.SourceArchivePath -Destination $correspondingSource
Copy-Item -LiteralPath (Join-Path $projectRoot 'src\browser-native\LICENSE-GPL-3.0.txt') `
    -Destination (Join-Path $stagingRoot 'LICENSE-OpenMCMBrowser-GPL-3.0.txt')

$buildInfo = [ordered]@{
    project = 'OpenMCM'
    version = $Version
    packageFormat = $PackageFormat
    OpenMCM_API = [ordered]@{
        version = 1
        prerelease = $true
        enabledByDefault = $false
        preferenceScope = 'savegame'
    }
    skyUICoexistence = 'Experimental; external real SkyUI 6 required in SkyUI mode; not yet verified in game'
    gameProductVersion = $gameVersion
    baseJournalSha256 = (Get-FileHash -LiteralPath $vanillaJournal -Algorithm SHA256).Hash
    outputJournalSha256 = (Get-FileHash -LiteralPath $finalSwf -Algorithm SHA256).Hash
    compatibilityPluginSha256 = (Get-FileHash -LiteralPath (Join-Path $dataRoot 'SkyUI_SE.esp') -Algorithm SHA256).Hash
    capricaIdentifierRepairs = $identifierRepairCount
    skyUICompatibility = '6.x MCM API v4'
    mcmHelperCompatibility = 'SkyUI_SE.esp / local form 0x000802 contract'
    browserIntegration = [ordered]@{
        scope = 'Redone-inspired browser; original Redone native persistence adapted; registry unchanged'
        registryLimit = 128
        saveLocalByDefault = $true
        inGameVerification = 'not verified'
        sourceArchive = ('source/' + [IO.Path]::GetFileName($browserNative.SourceArchivePath))
        sourceSha256 = (Get-FileHash -LiteralPath $browserNative.SourceArchivePath -Algorithm SHA256).Hash
        upstreamSourceSha256 = '0583CC8659873106FE4C746A6D9D09F0EE601D59C8D92053FE1B78FB30AB2CD6'
        dllSha256 = $browserNative.Sha256
        supportedGameRuntimes = $browserNative.SupportedGameRuntimes
    }
    nativeRuntime = [ordered]@{
        name = 'OpenMCMRuntime.dll'
        pluginVersion = $nativeRuntime.PluginVersion
        dllSha256 = $nativeRuntime.Sha256
        configSha256 = $nativeRuntime.ConfigSha256
        supportedGameRuntime = $nativeRuntime.SupportedGameRuntime
        disableChargenPrecacheDefault = $true
        optionalForMCM = $true
        nativeRegressionTests = 'passed'
        inGameVerification = 'not verified'
    }
}
[IO.File]::WriteAllText(
    (Join-Path $stagingRoot 'OpenMCM_BUILD.json'),
    ($buildInfo | ConvertTo-Json -Depth 4),
    [Text.UTF8Encoding]::new($false))

$packageRoot = $stagingRoot
if ($PackageFormat -eq 'Fomod') {
    $packageRoot = & (Join-Path $PSScriptRoot 'Build-FomodPackage.ps1') `
        -ProjectRoot $projectRoot -StagingRoot $stagingRoot -Version $Version `
        -Python $python.Source -Spriggit $tool.Spriggit -SkipTests:$SkipTests
}

# Include the complete editable project and the verified browser dependency
# sources in both package formats before generating the outer checksum manifest.
$completeSourceRelative = "source/OpenMCM-$Version-Source.zip"
$completeSourceArchive = Join-Path $packageRoot $completeSourceRelative
& $python.Source -B (Join-Path $projectRoot 'tools\package_openmcm_source.py') `
    --project-root $projectRoot --browser-source $browserNative.SourceArchivePath `
    --output $completeSourceArchive --version $Version
Assert-LastExitCode 'Packaging complete OpenMCM corresponding source'
$packageMetadataPath = Join-Path $packageRoot 'OpenMCM_BUILD.json'
$packageMetadata = Get-Content -LiteralPath $packageMetadataPath -Raw | ConvertFrom-Json
$packageMetadata | Add-Member -NotePropertyName 'correspondingSource' -NotePropertyValue ([ordered]@{
    archive = $completeSourceRelative
    sha256 = (Get-FileHash -LiteralPath $completeSourceArchive -Algorithm SHA256).Hash
    scope = 'complete OpenMCM project source plus pinned browser dependencies'
    license = 'GPL-3.0-or-later for original OpenMCM code; see third-party notices'
}) -Force
[IO.File]::WriteAllText($packageMetadataPath, ($packageMetadata | ConvertTo-Json -Depth 8),
    [Text.UTF8Encoding]::new($false))

$checksumPath = Join-Path $packageRoot 'OpenMCM_SHA256SUMS.txt'
$checksumLines = @(
    Get-ChildItem -LiteralPath $packageRoot -Recurse -File |
        Where-Object { $_.FullName -ne $checksumPath } |
        Sort-Object FullName |
        ForEach-Object {
            $relative = $_.FullName.Substring($packageRoot.Length + 1).Replace('\', '/')
            "$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash)  $relative"
        }
)
[IO.File]::WriteAllLines(
    $checksumPath,
    $checksumLines,
    [Text.UTF8Encoding]::new($false))

New-Item -ItemType Directory -Path $distRoot -Force | Out-Null
if (Test-Path -LiteralPath $archivePath) {
    throw "Refusing to overwrite an existing release archive: $archivePath"
}
Compress-Archive -Path (Join-Path $packageRoot '*') -DestinationPath $archivePath `
    -CompressionLevel Optimal

# Cheap installer safety gate also applies to -SkipTests builds. Validate bytes
# from the final ZIP through Nexus's encoding conversion, not just a parsed tree.
if ($PackageFormat -eq 'Fomod') {
    & (Join-Path $PSScriptRoot 'Test-FomodXml.ps1') -ArchivePath $archivePath
}

if (-not $SkipTests) {
    if ($PackageFormat -eq 'Fomod') {
        & $python.Source -B (Join-Path $projectRoot 'tools\check_fomod_package.py') $archivePath
        Assert-LastExitCode 'Checking every FOMOD selected-install combination and archive checksums'
    }
    else {
        & $python.Source -B (Join-Path $projectRoot 'tools\check_mcm_contract.py') `
            $archivePath --profile release
        Assert-LastExitCode 'Running the packaged release compatibility contract'
        & $python.Source -B (Join-Path $projectRoot 'tools\check_openmcm_api.py') $archivePath
        Assert-LastExitCode 'Checking the packaged opt-in OpenMCM API'
        & $python.Source -B (Join-Path $projectRoot 'tools\check_native_runtime.py') $archivePath
        Assert-LastExitCode 'Checking the packaged native runtime artifact'
    }
}

Write-Host ''
Write-Host "OpenMCM package: $archivePath"
Write-Host "Staged files:   $packageRoot"
Write-Host 'Choose SkyUI mode only with the real SkyUI package; standalone mode must not overwrite a full SkyUI installation.'
