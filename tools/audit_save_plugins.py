"""Read-only Skyrim SE save plugin-table audit; never reads Papyrus save payloads.

Header/table layout follows the local FallrimTools Header/ESS/PluginInfo reader.
LZ4 decoding stops after a bounded prefix containing the plugin names.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import zlib


def lz4_prefix(data: bytes, limit: int) -> bytes:
    output = bytearray()
    pos = 0
    while pos < len(data) and len(output) < limit:
        token = data[pos]
        pos += 1
        length = token >> 4
        if length == 15:
            while True:
                more = data[pos]
                pos += 1
                length += more
                if more != 255:
                    break
        if pos + length > len(data):
            raise ValueError("Truncated LZ4 literal")
        output.extend(data[pos:pos + min(length, limit - len(output))])
        pos += length
        if len(output) >= limit or pos == len(data):
            break
        offset = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        if not 0 < offset <= len(output):
            raise ValueError("Invalid LZ4 match offset")
        length = (token & 15) + 4
        if (token & 15) == 15:
            while True:
                more = data[pos]
                pos += 1
                length += more
                if more != 255:
                    break
        for _ in range(min(length, limit - len(output))):
            output.append(output[-offset])
    return bytes(output)


def save_plugins(path: Path) -> dict:
    data = path.read_bytes()
    if data[:13] != b"TESV_SAVEGAME":
        raise ValueError("Not a Skyrim save")
    header_size, version = struct.unpack_from("<II", data, 13)
    if version < 12 or not 40 < header_size < 256:
        raise ValueError("Unsupported save header")
    header_end = 17 + header_size
    width, height, compression = struct.unpack_from("<IIH", data, header_end - 10)
    body = header_end + 4 * width * height
    if body > len(data):
        raise ValueError("Truncated screenshot")
    limit = 1024 * 1024
    if compression:
        expected, compressed = struct.unpack_from("<II", data, body)
        payload = data[body + 8:]
        if compressed != len(payload) or expected < 5:
            raise ValueError("Invalid compressed lengths")
        if compression == 2:
            prefix = lz4_prefix(payload, min(limit, expected))
        elif compression == 1:
            prefix = zlib.decompressobj().decompress(payload, limit)
        else:
            raise ValueError("Unsupported compression")
    else:
        prefix = data[body:body + limit]
    form_version = prefix[0]
    table_size = struct.unpack_from("<I", prefix, 1)[0]
    table_end = 5 + table_size
    if form_version < 78 or table_end > len(prefix):
        raise ValueError("Unsupported or oversized plugin table")
    pos = 5

    def names(count: int) -> list[str]:
        nonlocal pos
        result = []
        for _ in range(count):
            size = struct.unpack_from("<H", prefix, pos)[0]
            pos += 2
            if pos + size > table_end:
                raise ValueError("Plugin name exceeds table")
            result.append(prefix[pos:pos + size].decode("utf-8"))
            pos += size
        return result

    full_count = prefix[pos]
    pos += 1
    full = names(full_count)
    light_count = struct.unpack_from("<H", prefix, pos)[0]
    pos += 2
    light = names(light_count)
    if pos != table_end:
        raise ValueError("Plugin table size mismatch")
    return {"file": path.name, "form_version": form_version,
            "full": full, "light": light}


def masters(path: Path) -> list[str]:
    with path.open("rb") as stream:
        header = stream.read(24)
        if header[:4] != b"TES4":
            raise ValueError("Not a TES4 plugin")
        size = struct.unpack_from("<I", header, 4)[0]
        if size > 1024 * 1024:
            raise ValueError("Oversized TES4 header")
        data = stream.read(size)
    result, pos, extended = [], 0, None
    while pos < len(data):
        kind, size = struct.unpack_from("<4sH", data, pos)
        pos += 6
        if kind == b"XXXX":
            if size != 4:
                raise ValueError("Invalid extended subrecord size")
            extended = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            continue
        if extended is not None:
            size, extended = extended, None
        if pos + size > len(data):
            raise ValueError("Truncated TES4 subrecord")
        if kind == b"MAST":
            result.append(data[pos:pos + size].rstrip(b"\0").decode("utf-8"))
        pos += size
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saves", type=Path, required=True)
    parser.add_argument("--plugins", type=Path, required=True)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()
    data_dir = args.game / "Data"
    explicit = [line[1:].strip() for line in args.plugins.read_text(encoding="utf-8-sig").splitlines()
                if line.startswith("*")]
    implicit = ["Skyrim.esm", "Update.esm", "Dawnguard.esm", "HearthFires.esm", "Dragonborn.esm"]
    ccc = args.game / "Skyrim.ccc"
    if ccc.exists():
        implicit.extend(line.strip() for line in ccc.read_text(encoding="utf-8-sig").splitlines()
                        if line.strip() and not line.startswith("#") and (data_dir / line.strip()).exists())
    active = {name.lower() for name in explicit + implicit}
    missing_masters = {}
    for name in explicit:
        path = data_dir / name
        if not path.exists():
            missing_masters[name] = ["PLUGIN FILE MISSING"]
            continue
        try:
            plugin_masters = masters(path)
        except (ValueError, struct.error, UnicodeError) as error:
            missing_masters[name] = ["HEADER PARSE FAILED: " + str(error)]
            continue
        absent = [master for master in plugin_masters if master.lower() not in active or not (data_dir / master).exists()]
        if absent:
            missing_masters[name] = absent
    print(json.dumps({"active_count": len(active), "active_missing_masters": missing_masters}))
    for path in sorted(args.saves.glob("*.ess"), key=lambda item: item.stat().st_mtime, reverse=True)[:args.count]:
        save = save_plugins(path)
        entries = save["full"] + save["light"]
        selected = [{"name": name, "kind": kind, "index": index}
                    for kind in ("full", "light") for index, name in enumerate(save[kind])
                    if any(term in name.lower() for term in ("fieldguide", "openmcm", "skyui", "mcmhelper"))]
        print(json.dumps({"file": save["file"], "form_version": save["form_version"],
                          "full_count": len(save["full"]), "light_count": len(save["light"]),
                          "mcm_entries": selected,
                          "saved_not_active": [name for name in entries if name.lower() not in active],
                          "saved_missing_files": [name for name in entries if not (data_dir / name).exists()],
                          "new_active_plugins": [name for name in explicit if name.lower() not in {entry.lower() for entry in entries}]}))


if __name__ == "__main__":
    main()
