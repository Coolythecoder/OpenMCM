# Read-only structural checks for local dump artifacts. Dot-sourcing this file
# does not start ProcDump, attach to a process, or read process memory.
# Layouts: Windows SDK minidumpapiset.h (MINIDUMP_HEADER/DIRECTORY/MEMORY*_LIST).
function Assert-MinidumpRange {
    param([UInt64] $Offset, [UInt64] $Size, [UInt64] $Length, [string] $Description)
    if ($Offset -gt $Length -or $Size -gt ($Length - $Offset)) {
        throw "$Description extends beyond the dump file."
    }
}

function Get-MinidumpValidation {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string] $LiteralPath, [switch] $RequireFullMemory)

    $stream = $null
    $reader = $null
    $result = [ordered]@{
        FullName = [IO.Path]::GetFullPath($LiteralPath)
        Length = 0
        StreamCount = 0
        FullMemory = $false
        StructurallyValid = $false
        Error = $null
    }
    try {
        # FileShare.Read refuses a file that is still open for writing.
        $stream = [IO.File]::Open($result.FullName, 'Open', 'Read', 'Read')
        $reader = [IO.BinaryReader]::new($stream)
        [UInt64] $length = $stream.Length
        $result.Length = $length
        Assert-MinidumpRange 0 32 $length 'Minidump header'
        if ($reader.ReadUInt32() -ne 0x504d444d) { throw 'Missing MDMP signature.' }
        if (($reader.ReadUInt32() -band 0xffff) -ne 42899) { throw 'Unsupported minidump version.' }
        [UInt64] $count = $reader.ReadUInt32()
        [UInt64] $directory = $reader.ReadUInt32()
        $result.StreamCount = $count
        if ($count -eq 0) { throw 'Minidump contains no streams.' }
        if ($directory -lt 32) { throw 'Stream directory overlaps the header.' }
        Assert-MinidumpRange $directory ($count * 12) $length 'Stream directory'
        $stream.Position = 24
        $result.FullMemory = (($reader.ReadUInt64() -band 2) -ne 0)
        if ($RequireFullMemory -and -not $result.FullMemory) { throw 'Full-memory dump was requested but its flag is missing.' }

        $types = [Collections.Generic.HashSet[UInt32]]::new()
        for ([UInt64] $index = 0; $index -lt $count; $index++) {
            $stream.Position = $directory + $index * 12
            $type = $reader.ReadUInt32()
            [UInt64] $size = $reader.ReadUInt32()
            [UInt64] $offset = $reader.ReadUInt32()
            $null = $types.Add($type)
            Assert-MinidumpRange $offset $size $length "Stream $index (type $type)"

            # Memory payloads sit outside their stream's descriptor array, so
            # directory bounds alone would accept a truncated dump tail.
            if ($type -eq 5) {
                if ($size -lt 4) { throw 'Memory-list stream is too short.' }
                $stream.Position = $offset
                [UInt64] $ranges = $reader.ReadUInt32()
                if (4 + $ranges * 16 -gt $size) { throw 'Memory-list descriptors are truncated.' }
                for ([UInt64] $range = 0; $range -lt $ranges; $range++) {
                    $stream.Position = $offset + 4 + $range * 16 + 8
                    [UInt64] $bytes = $reader.ReadUInt32()
                    [UInt64] $rva = $reader.ReadUInt32()
                    Assert-MinidumpRange $rva $bytes $length "Memory range $range"
                }
            } elseif ($type -eq 9) {
                if ($size -lt 16) { throw 'Memory64-list stream is too short.' }
                $stream.Position = $offset
                [UInt64] $ranges = $reader.ReadUInt64()
                [UInt64] $cursor = $reader.ReadUInt64()
                # Divide first: malicious counts must not overflow multiplication.
                if ($ranges -gt [Math]::Floor(($size - 16) / 16)) { throw 'Memory64-list descriptors are truncated.' }
                Assert-MinidumpRange $cursor 0 $length 'Memory64 payload start'
                for ([UInt64] $range = 0; $range -lt $ranges; $range++) {
                    $stream.Position = $offset + 16 + $range * 16 + 8
                    [UInt64] $bytes = $reader.ReadUInt64()
                    Assert-MinidumpRange $cursor $bytes $length "Memory64 range $range"
                    $cursor += $bytes
                }
            }
        }
        if (-not ($types.Contains(3) -or $types.Contains(8)) -or
            -not $types.Contains(4) -or -not $types.Contains(7) -or
            -not ($types.Contains(5) -or $types.Contains(9))) {
            throw 'Required thread, module, system-info, or memory stream is missing.'
        }
        $result.StructurallyValid = $true
    } catch {
        $result.Error = $_.Exception.Message
    } finally {
        if ($null -ne $reader) { $reader.Dispose() }
        elseif ($null -ne $stream) { $stream.Dispose() }
    }
    [PSCustomObject] $result
}

function Get-HangCaptureValidation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string] $LiteralPath,
        [ValidateRange(1, 10)][int] $ExpectedCount = 2,
        [switch] $RequireFullMemory
    )
    $dumps = @(Get-ChildItem -LiteralPath $LiteralPath -Filter '*.dmp' -File |
        Sort-Object Name | ForEach-Object {
            Get-MinidumpValidation -LiteralPath $_.FullName -RequireFullMemory:$RequireFullMemory
        })
    $valid = @($dumps | Where-Object StructurallyValid).Count
    [PSCustomObject]@{
        Complete = ($dumps.Count -eq $ExpectedCount -and $valid -eq $ExpectedCount)
        ExpectedCount = $ExpectedCount
        DumpCount = $dumps.Count
        ValidCount = $valid
        Dumps = $dumps
    }
}
