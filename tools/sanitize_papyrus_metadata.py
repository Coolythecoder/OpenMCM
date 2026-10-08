#!/usr/bin/env python3
"""Remove builder identity from generated Skyrim PEX header metadata only.

The source basename remains useful for diagnostics. Compiler user/machine become
OpenMCM/Build. The timestamp, string table, debug data and complete object/bytecode
tail are preserved byte-for-byte. This is not an opcode or identifier rewrite.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

from check_mcm_contract import _parse_skyrim_pex_envelope

MAX_PEX_BYTES = 16 * 1024 * 1024
MAX_FILES = 256


def sanitize_bytes(data: bytes) -> bytes:
    if len(data) > MAX_PEX_BYTES:
        raise ValueError("Generated PEX exceeds metadata-tool size bound")
    _parse_skyrim_pex_envelope(data)  # Validate before changing any bytes.
    offset = 16
    metadata = []
    for _ in range(3):
        length = struct.unpack_from(">H", data, offset)[0]
        offset += 2
        metadata.append(data[offset:offset + length].decode("utf-8"))
        offset += length
    basename = metadata[0].replace("\\", "/").rsplit("/", 1)[-1]
    if (not basename or basename in (".", "..") or ":" in basename or
            any(ord(character) < 32 for character in basename)):
        raise ValueError("Generated PEX has no safe source basename")
    replacement = bytearray(data[:16])
    for value in (basename, "OpenMCM", "Build"):
        encoded = value.encode("utf-8")
        replacement.extend(struct.pack(">H", len(encoded)))
        replacement.extend(encoded)
    replacement.extend(data[offset:])
    result = bytes(replacement)
    _parse_skyrim_pex_envelope(result)
    return result


def sanitize_path(target: Path) -> int:
    """Process one generated PEX or direct PEX children; never recurse."""
    if target.is_symlink() or (hasattr(target, "is_junction") and target.is_junction()):
        raise ValueError("Metadata target must not be a link")
    paths = sorted(target.glob("*.pex")) if target.is_dir() else [target]
    if not paths or len(paths) > MAX_FILES:
        raise ValueError("Metadata target must contain 1-256 generated PEX files")
    prepared = []
    for path in paths:
        if (path.suffix.casefold() != ".pex" or not path.is_file() or
                path.is_symlink() or path.stat().st_size > MAX_PEX_BYTES):
            raise ValueError("Metadata input must be a bounded regular PEX file")
        original = path.read_bytes()
        prepared.append((path, original, sanitize_bytes(original)))
    # Validate every input before modifying any file in this generated directory.
    for path, original, sanitized in prepared:
        if sanitized != original:
            path.write_bytes(sanitized)
    return len(prepared)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    try:
        count = sanitize_path(args.target)
    except (OSError, ValueError) as error:
        print(f"PEX metadata normalization failed: {error}", file=sys.stderr)
        return 1
    print(f"Normalized private compiler metadata in {count} generated PEX file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
