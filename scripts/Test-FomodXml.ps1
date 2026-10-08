[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $ArchivePath
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# Reproduce the string-to-stream path used by Nexus's FOMOD XML validator,
# not just .NET's direct parsing of the original legal UTF-8 archive bytes.
# Pinned implementation: XmlScriptType.StringStream / Validate, lines 94-139:
# https://github.com/Nexus-Mods/fomod-installer/blob/5f0baede15f9e6d38065b05698a358975b1f5eb9/src/InstallScripting/XmlScript/XmlScriptType.cs#L94
# Its regex removes only a DOUBLE-QUOTED encoding declaration, then it writes
# UTF-16BE with BOM. A surviving single-quoted UTF-8 declaration conflicts with
# those bytes and fails at line 1, position 39. Both input XML files are checked
# conservatively through this path. This is not a FOMOD schema or UI test.

function Test-NexusXmlStringStream {
    param([Parameter(Mandatory)] [string] $XmlText)

    $memory = [IO.MemoryStream]::new()
    $writer = $null
    $reader = $null
    try {
        $writer = [IO.StreamWriter]::new($memory, [Text.UnicodeEncoding]::new($true, $true))
        # This regex and replacement intentionally match the pinned Nexus code.
        $normalized = [Text.RegularExpressions.Regex]::Replace($XmlText, '^([^>]*)encoding="[^"]+"', '$1')
        $writer.Write($normalized)
        $writer.Flush()
        $memory.Position = 0
        $reader = [Xml.XmlReader]::Create($memory)
        while ($reader.Read()) { }
        return [pscustomobject]@{ Success = $true; Message = ''; Line = 0; Position = 0 }
    }
    catch {
        $failure = $_.Exception
        while ($null -ne $failure.InnerException) { $failure = $failure.InnerException }
        if ($failure -isnot [Xml.XmlException]) { throw }
        return [pscustomobject]@{
            Success = $false
            Message = $failure.Message
            Line = $failure.LineNumber
            Position = $failure.LinePosition
        }
    }
    finally {
        if ($null -ne $reader) { $reader.Dispose() }
        if ($null -ne $writer) { $writer.Dispose() }
        $memory.Dispose()
    }
}

# Guard the regression mechanism itself: otherwise a direct string parse could
# pass the published broken header and give a false success again.
$singleQuoted = '<?xml version=''1.0'' encoding=''utf-8''?>' + "`n<config />"
$doubleQuoted = '<?xml version="1.0" encoding="utf-8"?>' + "`n<config />"
$expectedFailure = Test-NexusXmlStringStream -XmlText $singleQuoted
if ($expectedFailure.Success -or $expectedFailure.Line -ne 1 -or
    $expectedFailure.Position -ne 39 -or -not $expectedFailure.Message.Contains('0x00')) {
    throw "FOMOD regression self-check failed: expected invalid NUL at line 1, position 39; got $($expectedFailure | ConvertTo-Json -Compress)"
}
foreach ($supportedHeader in @($doubleQuoted, '<config />')) {
    $expectedSuccess = Test-NexusXmlStringStream -XmlText $supportedHeader
    if (-not $expectedSuccess.Success) {
        throw "FOMOD regression self-check failed: supported header did not parse: $($expectedSuccess.Message)"
    }
}
Write-Host 'PASS FOMOD preprocessing self-check: single-quoted header fails at 1:39; double-quoted and absent headers pass.'

if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
    throw "FOMOD archive not found: $ArchivePath"
}
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead([IO.Path]::GetFullPath($ArchivePath))
$failures = [Collections.Generic.List[string]]::new()
try {
    foreach ($relative in @('fomod/ModuleConfig.xml', 'fomod/info.xml')) {
        $entryMatches = @($archive.Entries | Where-Object { $_.FullName -ieq $relative })
        if ($entryMatches.Count -ne 1) {
            $failures.Add("Expected exactly one '$relative' in ZIP; found $($entryMatches.Count).")
            continue
        }
        $entryStream = $entryMatches[0].Open()
        $textReader = $null
        try {
            # Same initial decoding as Nexus TextUtil.ByteToString: UTF-8
            # default with BOM detection. Nothing is extracted or rewritten.
            $textReader = [IO.StreamReader]::new($entryStream, $true)
            $xmlText = $textReader.ReadToEnd()
        }
        finally {
            if ($null -ne $textReader) { $textReader.Dispose() }
            $entryStream.Dispose()
        }
        $result = Test-NexusXmlStringStream -XmlText $xmlText
        if ($result.Success) {
            Write-Host "PASS Nexus XML preprocessing: $relative"
        }
        else {
            $failures.Add("${relative}: $($result.Message)")
        }
    }
}
finally { $archive.Dispose() }

if ($failures.Count -ne 0) {
    throw ('FOMOD XML preprocessing validation failed: ' + ($failures -join ' | '))
}
Write-Host 'PASS both FOMOD XML files parsed after Nexus preprocessing.'
