#!/usr/bin/env python3
"""Validate the selected OpenMCM-with-SkyUI payload, not an installed game.

This separate contract never relaxes the standalone package checker. It checks
ownership, the status-only companion plugin, and the existing compiled MCM ABI.
It does not prove runtime compatibility or replace an in-game integration test.
Only the standard library is required; directory and ZIP inputs are read-only.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import zipfile
import zlib
from pathlib import Path

from check_mcm_contract import (
    PackageView,
    Report,
    _decode_zstring,
    _parse_skyrim_pex_envelope,
    _plugin_records,
    _validate_checksum_manifest,
    _validate_pex,
    _validate_papyrus_source,
    _validate_token_asset,
)
from check_native_runtime import validate_dll, validate_ini
from check_openmcm_api import API_PATHS, API_SCRIPTS, validate_view as validate_api_view


STATUS_FORM_ID = 0x02000800  # Skyrim.esm, SkyUI_SE.esp, then this plugin.
STATUS_EDITOR_ID = "OpenMCM_ConfigMenuInstance"
SCRIPTS = ("SKI_ConfigBase", "SKI_ConfigManager", "OpenMCM_ConfigMenu")
REQUIRED = frozenset(
    ("openmcm.esp", "seq/openmcm.seq", "interface/quest_journal.swf")
    + tuple(f"scripts/{name.casefold()}.pex" for name in SCRIPTS)
) | API_PATHS
SOURCES = frozenset(f"source/scripts/{name.casefold()}.psc" for name in SCRIPTS + API_SCRIPTS)
NATIVE = frozenset(("skse/plugins/openmcmruntime.dll", "skse/plugins/openmcmruntime.ini"))
BROWSER = frozenset(("skse/plugins/openmcmbrowser.dll",))
ALLOWED = REQUIRED | SOURCES | NATIVE | BROWSER
# These are package-root documentation, never arbitrary Data payloads.
ROOT_DOCUMENTS = frozenset(
    ("readme.md", "readme-skyui.md", "compatibility.md", "changelog.md", "release-notes.md",
     "license", "license.txt", "openmcm_sha256sums.txt")
)
DEFAULT_CONTRACT = Path(__file__).resolve().parents[1] / "tests/contracts/skyui6_mcm_contract.json"


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def take(self, length: int) -> bytes:
        if length < 0 or self.offset + length > len(self.data):
            raise ValueError(f"truncated data at byte {self.offset}")
        value = self.data[self.offset:self.offset + length]
        self.offset += length
        return value

    def integer(self, fmt: str) -> int:
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]

    def string(self, endian: str = "<") -> str:
        return self.take(self.integer(endian + "H")).decode("utf-8")

    def done(self) -> None:
        if self.offset != len(self.data):
            raise ValueError(f"{len(self.data) - self.offset} trailing byte(s)")


def _subrecords(data: bytes) -> list[tuple[bytes, bytes]]:
    """Strict subrecord boundaries, including short trailing junk and XXXX."""
    reader = Reader(data)
    result = []
    while reader.offset < len(data):
        signature = reader.take(4)
        length = reader.integer("<H")
        if signature == b"XXXX":
            if length != 4:
                raise ValueError("invalid XXXX size")
            length = reader.integer("<I")
            signature = reader.take(4)
            reader.take(2)
            if signature == b"XXXX":
                raise ValueError("nested XXXX size")
        result.append((signature, reader.take(length)))
    return result


def _script(reader: Reader) -> tuple[str, dict[str, object]]:
    name = reader.string()
    reader.take(1)  # Script status.
    properties: dict[str, object] = {}
    for _ in range(reader.integer("<H")):
        key = reader.string()
        kind = reader.integer("<B")
        reader.take(1)  # Property status.
        if key in properties:
            raise ValueError(f"duplicate script property {key}")
        if kind == 2:
            value: object = reader.string()
        elif kind == 12:
            value = [reader.string() for _ in range(reader.integer("<I"))]
        else:
            raise ValueError(f"unexpected status-quest property type {kind}: {key}")
        properties[key] = value
    return name, properties


def _validate_vmad(data: bytes, report: Report) -> None:
    reader = Reader(data)
    version, object_format, count = (reader.integer("<H") for _ in range(3))
    if (version, object_format, count) != (5, 2, 1):
        raise ValueError("status VMAD must be version 5, object format 2, one script")
    name, properties = _script(reader)
    report.check(name == "OpenMCM_ConfigMenu", "STATUS_SCRIPT_MISMATCH: only OpenMCM_ConfigMenu may be attached")
    report.check(
        properties == {"ModName": "OpenMCM", "Pages": ["Status"]},
        "STATUS_PROPERTIES_MISMATCH: expected only ModName=OpenMCM and Pages=[Status]",
    )
    # QUST fragment section, then the one reload alias. No manager fragment.
    extra_version = reader.integer("<B")
    fragment_count = reader.integer("<H")
    fragment_file = reader.string()
    if (extra_version, fragment_count, fragment_file) != (2, 0, ""):
        raise ValueError("status quest must not contain quest fragments")
    if reader.integer("<H") != 1:
        raise ValueError("status quest must have exactly one VMAD reload alias")
    unused, alias_id, owner = reader.integer("<H"), reader.integer("<H"), reader.integer("<I")
    report.check(
        (unused, alias_id, owner) == (0, 0, STATUS_FORM_ID),
        "STATUS_ALIAS_OWNER_MISMATCH: reload alias must belong to OpenMCM.esp:000800, alias 0",
    )
    if tuple(reader.integer("<H") for _ in range(3)) != (5, 2, 1):
        raise ValueError("status reload alias must have exactly one version-5 script")
    alias_script, alias_properties = _script(reader)
    report.check(
        alias_script == "SKI_PlayerLoadGameAlias" and not alias_properties,
        "STATUS_ALIAS_SCRIPT_MISMATCH: use SkyUI's existing SKI_PlayerLoadGameAlias without replacing it",
    )
    reader.done()


def _validate_plugin(blob: bytes, report: Report) -> None:
    try:
        if not blob.startswith(b"TES4"):
            raise ValueError("plugin must begin with TES4")
        records = list(_plugin_records(blob))
        if not report.check(
            [record[0] for record in records] == [b"TES4", b"QUST"],
            "STATUS_RECORDS_MISMATCH: companion must contain only TES4 and one status QUST; no overrides or second manager",
        ):
            return
        header, quest = records
        report.check(header[1] == 0, "STATUS_HEADER_FORM_MISMATCH: TES4 FormID must be zero")
        report.check(bool(header[2] & 0x200), "STATUS_PLUGIN_FLAGS: companion must be ESL-flagged")
        report.check(
            not (header[2] & (0x1 | 0x80)),
            "STATUS_PLUGIN_FLAGS: companion must not be an ESM or localized-string-table plugin",
        )
        header_fields = _subrecords(header[3])
        for signature, _ in header_fields:
            report.check(
                signature in {b"HEDR", b"CNAM", b"SNAM", b"MAST", b"DATA", b"INTV"},
                f"STATUS_HEADER_SUBRECORD_FORBIDDEN: {signature!r}",
            )
        hedr = [data for signature, data in header_fields if signature == b"HEDR"]
        report.check(len(hedr) == 1 and len(hedr[0]) == 12, "STATUS_HEADER_HEDR_MISSING: one complete HEDR required")
        masters = [_decode_zstring(payload) for signature, payload in header_fields if signature == b"MAST"]
        report.check(
            masters == ["Skyrim.esm", "SkyUI_SE.esp"],
            f"STATUS_MASTERS_MISMATCH: expected Skyrim.esm then SkyUI_SE.esp, found {masters}",
        )
        report.check(
            quest[1] == STATUS_FORM_ID,
            f"STATUS_FORM_MISMATCH: expected own FormID 0x{STATUS_FORM_ID:08X}, found 0x{quest[1]:08X}; never override a SkyUI quest",
        )
        report.check(not (quest[2] & 0x20), "STATUS_QUEST_DELETED: status quest must not be deleted")
        fields = _subrecords(quest[3])
        allowed = {b"EDID", b"VMAD", b"FULL", b"DNAM", b"NEXT", b"ANAM", b"ALST", b"ALID", b"FNAM", b"ALFR", b"VTCK", b"ALED"}
        for signature, _ in fields:
            report.check(signature in allowed, f"STATUS_SUBRECORD_FORBIDDEN: {signature!r}")
        for signature in allowed:
            count = sum(sig == signature for sig, _ in fields)
            report.check(count <= 1, f"STATUS_SUBRECORD_DUPLICATE: {signature!r}")
        by_name = dict(fields)
        report.check(
            by_name.get(b"EDID") == (STATUS_EDITOR_ID + "\0").encode(),
            f"STATUS_EDITOR_ID_MISMATCH: expected {STATUS_EDITOR_ID}",
        )
        dnam = by_name.get(b"DNAM", b"")
        report.check(
            len(dnam) == 12 and struct.unpack_from("<H", dnam)[0] & 0x111 == 0x111,
            "STATUS_QUEST_FLAGS_MISMATCH: expected StartGameEnabled and RunOnce initialization flags",
        )
        report.check(by_name.get(b"ALST") == struct.pack("<I", 0), "STATUS_PLAYER_ALIAS_MISSING: alias 0 required")
        report.check(by_name.get(b"ALID") == b"PlayerAlias\0", "STATUS_PLAYER_ALIAS_NAME_MISMATCH: expected PlayerAlias")
        report.check(by_name.get(b"ALFR") == struct.pack("<I", 0x14), "STATUS_PLAYER_REFERENCE_MISMATCH: expected Skyrim.esm player 000014")
        report.check(by_name.get(b"ANAM") == struct.pack("<I", 1), "STATUS_ALIAS_COUNT_MISMATCH: next alias ID must be 1")
        report.check(by_name.get(b"ALED") == b"", "STATUS_ALIAS_END_MISSING")
        _validate_vmad(by_name.get(b"VMAD", b""), report)
    except (ValueError, UnicodeDecodeError, struct.error, zlib.error) as exc:
        report.check(False, f"STATUS_PLUGIN_PARSE_ERROR: {exc}")


def _pex_parent(blob: bytes) -> str:
    # The existing envelope validator checks bounds and object sizes first.
    reader = Reader(blob)
    reader.take(16)
    for _ in range(3):
        reader.string(">")
    strings = [reader.string(">") for _ in range(reader.integer(">H"))]
    if reader.integer(">B"):
        reader.take(8)
        for _ in range(reader.integer(">H")):
            reader.take(7)
            reader.take(reader.integer(">H") * 2)
    reader.take(reader.integer(">H") * 3)
    if reader.integer(">H") != 1:
        raise ValueError("exactly one PEX object required")
    reader.take(6)  # Object-name index and size.
    index = reader.integer(">H")
    if index >= len(strings):
        raise ValueError("invalid parent string index")
    return strings[index]


def _directory_preflight(target: Path) -> None:
    """PackageView already validates ZIP paths; add disk alias/path checks."""
    if not target.is_dir():
        return
    root = target.resolve()
    seen: set[str] = set()
    for directory, folders, filenames in os.walk(root):
        for name in folders + filenames:
            path = Path(directory) / name
            rel = path.relative_to(root).as_posix()
            is_reparse = bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)
            if path.is_symlink() or is_reparse or not path.resolve().is_relative_to(root):
                raise ValueError(f"unsafe directory entry: {rel}")
            if ":" in name or "\\" in name or name.rstrip(" .") != name:
                raise ValueError(f"unsafe directory entry: {rel}")
            if rel.casefold() in seen:
                raise ValueError(f"duplicate case-insensitive directory path: {rel}")
            seen.add(rel.casefold())


def _zip_preflight(target: Path) -> None:
    # On Windows ZipInfo.filename normalizes '\\' before PackageView sees it;
    # orig_filename preserves the stored spelling (including embedded NULs).
    if not target.is_file() or not zipfile.is_zipfile(target):
        return
    with zipfile.ZipFile(target) as archive:
        for info in archive.infolist():
            raw = info.orig_filename
            if "\\" in raw or any(ord(char) < 32 for char in raw):
                raise ValueError(f"unsafe zip entry path: {raw!r}")
            if (info.external_attr >> 16) & 0xF000 == 0xA000:
                raise ValueError(f"unsafe zip symlink entry: {raw!r}")


def validate_package(target: str | Path, *, contract_path: str | Path | None = None) -> Report:
    """Read a selected coexistence payload and return all static findings."""
    target = Path(target)
    report = Report(str(target.resolve()), "skyui-coexist")
    report.warn("Static payload/ABI validation only; Skyrim integration and migration require in-game testing.")
    try:
        _directory_preflight(target)
        _zip_preflight(target)
        manifest = json.loads(Path(contract_path or DEFAULT_CONTRACT).read_text(encoding="utf-8"))
        if manifest.get("schema_version") != 1:
            raise ValueError("unsupported MCM contract schema")
        with PackageView(target) as view:
            wrapped = any(entry.key.startswith("data/") for entry in view.entries)
            payload: set[str] = set()
            for entry in view.entries:
                parts = entry.name.split("/")
                if any(":" in part or part.rstrip(" .") != part for part in parts):
                    report.check(False, f"UNSAFE_PACKAGE_PATH: {entry.name}")
                if wrapped and entry.key in ROOT_DOCUMENTS:
                    continue
                key = entry.key[5:] if wrapped and entry.key.startswith("data/") else entry.key
                if not wrapped and entry.key == "openmcm_sha256sums.txt":
                    continue
                report.check(key in ALLOWED, f"COEXIST_PAYLOAD_FORBIDDEN: {entry.name}")
                if wrapped and not entry.key.startswith("data/"):
                    report.check(False, f"MIXED_DATA_LAYOUT: {entry.name} is outside Data")
                report.check(key not in payload, f"COEXIST_PAYLOAD_DUPLICATE: {entry.name}")
                payload.add(key)
            for path in sorted(REQUIRED):
                report.check(path in payload, f"COEXIST_PAYLOAD_MISSING: {path}")
            native_present = payload & NATIVE
            report.check(not native_present or native_present == NATIVE, "COEXIST_NATIVE_PAIR_MISSING: optional DLL and INI must be selected together")
            if native_present == NATIVE:
                for native_path, validator in (
                    ("SKSE/Plugins/OpenMCMRuntime.dll", validate_dll),
                    ("SKSE/Plugins/OpenMCMRuntime.ini", validate_ini),
                ):
                    native_entry = view.get_data_path(native_path)
                    assert native_entry is not None
                    try:
                        validator(view.read_bytes(native_entry))
                        report.check(True, f"COEXIST_NATIVE_INVALID: {native_path}")
                    except ValueError as exc:
                        report.check(False, f"COEXIST_NATIVE_INVALID: {native_path}: {exc}")
            _validate_checksum_manifest(view, report, required=view.is_zip)

            browser_entry = view.get_data_path("SKSE/Plugins/OpenMCMBrowser.dll")
            if browser_entry is not None:
                from check_browser_native import validate_dll as validate_browser_dll
                try:
                    validate_browser_dll(view.read_bytes(browser_entry))
                    report.check(True, "COEXIST_BROWSER_INVALID")
                except ValueError as exc:
                    report.check(False, f"COEXIST_BROWSER_INVALID: {exc}")

            entry = view.get_data_path("OpenMCM.esp")
            if entry is not None:
                _validate_plugin(view.read_bytes(entry), report)
            sequence = view.get_data_path("Seq/OpenMCM.seq")
            if sequence is not None:
                report.check(
                    view.read_bytes(sequence) == struct.pack("<I", STATUS_FORM_ID),
                    "COEXIST_SEQ_MISMATCH: expected only own status FormID 0x02000800, not a SkyUI/second manager quest",
                )
            contracts = {item["script"]: item for item in manifest["papyrus"]}
            for script in SCRIPTS:
                contract = contracts.get(script)
                if contract is None:
                    raise ValueError(f"MCM contract missing {script}")
                _validate_pex(view, report, contract)
                if view.get_data_path(f"Source/Scripts/{script}.psc") is not None:
                    _validate_papyrus_source(view, report, contract)
                pex_entry = view.get_data_path(f"Scripts/{script}.pex")
                if pex_entry is None:
                    continue
                blob = view.read_bytes(pex_entry)
                try:
                    strings, objects = _parse_skyrim_pex_envelope(blob)
                    report.check(objects == [script], f"COEXIST_PEX_OBJECT_MISMATCH: {script}")
                    report.check(_pex_parent(blob).casefold() == str(contract["extends"]).casefold(), f"COEXIST_PEX_PARENT_MISMATCH: {script}")
                    for literal in contract.get("required_literals", []):
                        report.check(literal in strings, f"COEXIST_PEX_LITERAL_MISSING: {script}: {literal}")
                except (ValueError, UnicodeDecodeError, struct.error) as exc:
                    report.check(False, f"COEXIST_PEX_PARSE_ERROR: {script}: {exc}")
            for asset in manifest["ui_assets"]:
                _validate_token_asset(view, report, asset, "release")
            validate_api_view(view, report)
    except (OSError, ValueError, KeyError) as exc:
        report.check(False, f"COEXIST_PACKAGE_INVALID: {exc}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="selected coexistence Data tree, root/Data tree, or ZIP")
    parser.add_argument("--json", action="store_true", help="print a machine-readable Report")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT, help="existing MCM ABI contract JSON")
    args = parser.parse_args(argv)
    report = validate_package(args.target, contract_path=args.contract)
    if args.json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        print(f"OpenMCM / SkyUI coexistence payload: {'PASS' if report.ok else 'FAIL'} ({report.checks} checks)")
        for message in report.errors:
            print(f"ERROR: {message}")
        for message in report.warnings:
            print(f"NOTE: {message}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
