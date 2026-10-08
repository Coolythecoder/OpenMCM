#!/usr/bin/env python3
"""Repair known Caprica 0.3 custom-type casing in complete PEX table entries.

Metadata and arbitrary substrings are never changed. Replacements have equal
byte lengths and preserve every bytecode offset/index. This does not compile or
otherwise rewrite the PEX. Used by the optional Field Guide example builder.
"""
from __future__ import annotations

import argparse
import re
import struct
from pathlib import Path

from check_mcm_contract import _parse_skyrim_pex_envelope


def repair_bytes(data: bytes) -> tuple[bytes, int]:
    _parse_skyrim_pex_envelope(data)  # Reject malformed input before mutation.
    result = bytearray(data)
    offset = 16

    def string_span() -> tuple[int, int]:
        nonlocal offset
        length = struct.unpack_from(">H", data, offset)[0]
        start = offset + 2
        offset = start + length
        return start, length

    for _ in range(3):
        string_span()  # Source, compiler user, compiler machine: untouched.
    count = struct.unpack_from(">H", data, offset)[0]
    offset += 2
    repairs = 0
    for _ in range(count):
        start, length = string_span()
        symbol = data[start:start + length].decode("utf-8")
        if re.fullmatch(r"sKI_[A-Za-z0-9_]+(?:\[\])?", symbol):
            result[start] = ord("S")
        elif re.fullmatch(r"openMCM(?:_[A-Za-z0-9_]+)?(?:\[\])?", symbol):
            result[start] = ord("O")
        elif symbol == "stringUtil":
            result[start] = ord("S")
        else:
            continue
        repairs += 1
    return bytes(result), repairs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pex", type=Path)
    args = parser.parse_args()
    repaired, count = repair_bytes(args.pex.read_bytes())
    if count:
        args.pex.write_bytes(repaired)
    print(f"Canonicalized {count} custom-type reference(s): {args.pex.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
