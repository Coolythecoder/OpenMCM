#!/usr/bin/env python3
"""Read-only validation of OpenMCM's optional native runtime release files.

Uses only the standard library and never loads the DLL. Metadata offsets and
packed versions follow the official SKSE 2.3.1 PluginAPI.h/skse_version.h.
This is a structural artifact check, not proof that the patch works in game.
"""

from __future__ import annotations

import argparse
import configparser
import struct
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path


RUNTIME_VERSION = 0x01070680  # MAKE_EXE_VERSION(1, 7, 104)
SKSE_VERSION = 0x02030010  # MAKE_EXE_VERSION(2, 3, 1)
METADATA_SIZE = 0x350
DLL_PATH = "data/skse/plugins/openmcmruntime.dll"
INI_PATH = "data/skse/plugins/openmcmruntime.ini"
IMAGE_SCN_MEM_EXECUTE = 0x20000000
IMAGE_SCN_MEM_READ = 0x40000000


class ValidationError(ValueError):
    """A release artifact does not satisfy the runtime contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


@dataclass(frozen=True)
class Section:
    rva: int
    virtual_size: int
    raw: int
    raw_size: int
    flags: int


class PEImage:
    def __init__(self, data: bytes):
        self.data = data
        require(self.read(0, 2) == b"MZ", "DLL has no DOS MZ header")
        pe = self.u32(0x3C)
        require(self.read(pe, 4) == b"PE\0\0", "DLL has no PE signature")
        require(self.u16(pe + 4) == 0x8664, "DLL must target AMD64")
        count = self.u16(pe + 6)
        require(0 < count <= 96, "Invalid PE section count")
        optional_size = self.u16(pe + 20)
        require(self.u16(pe + 22) & 0x2000 != 0, "PE image is not a DLL")
        optional = pe + 24
        require(optional_size >= 120, "Truncated PE32+ optional header")
        self.read(optional, optional_size)
        require(self.u16(optional) == 0x20B, "DLL must use PE32+ format")
        require(self.u32(optional + 108) >= 1, "PE export directory is missing")
        self.export_rva = self.u32(optional + 112)
        self.export_size = self.u32(optional + 116)
        require(self.export_rva != 0 and self.export_size >= 40,
                "PE export directory is missing or truncated")
        table = optional + optional_size
        self.read(table, count * 40)
        self.sections = []
        for index in range(count):
            start = table + index * 40
            virtual_size, rva, raw_size, raw = struct.unpack_from("<IIII", data, start + 8)
            flags = self.u32(start + 36)
            if raw_size:
                self.read(raw, raw_size)
            self.sections.append(Section(rva, virtual_size, raw, raw_size, flags))
        # Ambiguous section mappings are unsafe even if one mapping looks valid.
        allocated = sorted((s.rva, s.rva + max(s.virtual_size, s.raw_size))
                           for s in self.sections if max(s.virtual_size, s.raw_size))
        require(all(a[1] <= b[0] for a, b in zip(allocated, allocated[1:])),
                "PE sections have overlapping RVA ranges")

    def read(self, offset: int, size: int) -> bytes:
        require(offset >= 0 and size >= 0 and offset + size <= len(self.data),
                "PE structure points outside the file")
        return self.data[offset:offset + size]

    def u16(self, offset: int) -> int:
        return struct.unpack("<H", self.read(offset, 2))[0]

    def u32(self, offset: int) -> int:
        return struct.unpack("<I", self.read(offset, 4))[0]

    def mapping(self, rva: int, size: int) -> tuple[int, Section]:
        for section in self.sections:
            delta = rva - section.rva
            if 0 <= delta and delta + size <= section.raw_size:
                return section.raw + delta, section
        raise ValidationError(f"RVA 0x{rva:X} is not backed by {size} file bytes")

    def read_rva(self, rva: int, size: int) -> bytes:
        offset, _ = self.mapping(rva, size)
        return self.read(offset, size)

    def ascii_rva(self, rva: int) -> str:
        offset, section = self.mapping(rva, 1)
        available = min(512, section.raw + section.raw_size - offset)
        return ascii_z(self.read(offset, available), "export name")

    def exports(self) -> dict[str, int]:
        directory = self.read_rva(self.export_rva, 40)
        functions, names, function_table, name_table, ordinal_table = struct.unpack_from(
            "<IIIII", directory, 20)
        require(0 < functions <= 65536 and 0 < names <= 65536,
                "Invalid export table counts")
        addresses = struct.unpack("<" + "I" * functions,
                                  self.read_rva(function_table, functions * 4))
        name_rvas = struct.unpack("<" + "I" * names, self.read_rva(name_table, names * 4))
        ordinals = struct.unpack("<" + "H" * names, self.read_rva(ordinal_table, names * 2))
        exports = {}
        for name_rva, ordinal in zip(name_rvas, ordinals):
            require(ordinal < functions, "Export ordinal exceeds function table")
            name = self.ascii_rva(name_rva)
            require(name not in exports, "Duplicate named PE export")
            exports[name] = addresses[ordinal]
        return exports

    def require_export(self, exports: dict[str, int], name: str, executable: bool,
                       size: int = 1) -> bytes:
        require(name in exports, f"Missing actual PE export: {name}")
        rva = exports[name]
        require(not self.export_rva <= rva < self.export_rva + self.export_size,
                f"{name} must not be a forwarded export")
        offset, section = self.mapping(rva, size)
        require(bool(section.flags & IMAGE_SCN_MEM_EXECUTE) == executable,
                f"{name} must be a {'code' if executable else 'data'} export")
        require(section.flags & IMAGE_SCN_MEM_READ != 0,
                f"{name} must be in a readable section")
        return self.read(offset, size)


def ascii_z(data: bytes, label: str) -> str:
    terminator = data.find(b"\0")
    require(terminator >= 0, f"{label} is not null-terminated")
    try:
        return data[:terminator].decode("ascii")
    except UnicodeDecodeError as error:
        raise ValidationError(f"{label} is not ASCII") from error


def validate_dll(data: bytes) -> dict[str, int | str]:
    image = PEImage(data)
    exports = image.exports()
    image.require_export(exports, "SKSEPlugin_Load", executable=True)
    metadata = image.require_export(exports, "SKSEPlugin_Version", executable=False,
                                    size=METADATA_SIZE)
    data_version, plugin_version = struct.unpack_from("<II", metadata)
    require(data_version == 1, "SKSE metadata dataVersion must equal 1")
    require(plugin_version > 0, "SKSE metadata pluginVersion must be nonzero")
    name = ascii_z(metadata[0x008:0x108], "plugin name")
    require(name == "OpenMCMRuntime", "Unexpected SKSE metadata plugin name")
    ascii_z(metadata[0x108:0x208], "author")
    ascii_z(metadata[0x208:0x304], "support email")
    extended, independence = struct.unpack_from("<II", metadata, 0x304)
    require(extended == 0 and independence == 0,
            "Runtime-specific patch must not claim version independence")
    versions = struct.unpack_from("<16I", metadata, 0x30C)
    require(versions == (RUNTIME_VERSION,) + (0,) * 15,
            "Compatibility must contain only Skyrim 1.7.104.0, then zero terminators")
    minimum = struct.unpack_from("<I", metadata, 0x34C)[0]
    require(minimum <= SKSE_VERSION, "Minimum SKSE version excludes supported SKSE 2.3.1")
    return {"plugin": name, "plugin_version": plugin_version,
            "runtime": RUNTIME_VERSION, "minimum_skse": minimum}


def validate_ini(data: bytes) -> None:
    config = configparser.ConfigParser(interpolation=None)
    try:
        config.read_string(data.decode("utf-8-sig"))
        require(config.has_section("Patches"), "INI must contain [Patches]")
        require(config.get("Patches", "DisableChargenPrecache", fallback="").strip() == "1",
                "Release default DisableChargenPrecache must equal 1")
    except (UnicodeDecodeError, configparser.Error) as error:
        raise ValidationError(f"Invalid runtime INI: {error}") from error


def package_files(target: Path) -> dict[str, bytes]:
    required = {DLL_PATH, INI_PATH}
    found: dict[str, bytes] = {}

    def keep(name: str, read) -> None:
        normalized = name.replace("\\", "/").casefold()
        if normalized in required:
            require(normalized not in found, f"Duplicate runtime package file: {name}")
            found[normalized] = read()

    if target.is_dir():
        for path in target.rglob("*"):
            if path.is_file():
                keep(path.relative_to(target).as_posix(), path.read_bytes)
    elif target.is_file() and zipfile.is_zipfile(target):
        with zipfile.ZipFile(target) as archive:
            for entry in archive.infolist():
                if not entry.is_dir():
                    keep(entry.filename, lambda entry=entry: archive.read(entry))
    else:
        raise ValidationError("Target must be an unpacked release directory or ZIP")
    for name in sorted(required):
        require(name in found, f"Missing runtime package file: {name}")
    return found


def validate(target: Path | str) -> dict[str, int | str]:
    files = package_files(Path(target))
    metadata = validate_dll(files[DLL_PATH])
    validate_ini(files[INI_PATH])
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Unpacked release root or release ZIP")
    args = parser.parse_args(argv)
    try:
        result = validate(args.target)
    except (ValidationError, OSError, zipfile.BadZipFile) as error:
        print(f"Native runtime validation FAILED: {error}", file=sys.stderr)
        return 1
    print(f"Native runtime validation passed: {result['plugin']}, "
          "AMD64 exports/metadata, Skyrim 1.7.104 only, precache fix enabled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
