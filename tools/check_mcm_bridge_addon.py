#!/usr/bin/env python3
"""Validate the separate BASIC MCM Bridge adapter, not gameplay or legal approval.

The installed payload must contain exactly the two OpenMCM SDK scripts and their
sources. Bridge's host scripts, UI and DLL must never be distributed as runtime
overrides. Source dependencies are permitted only inside the corresponding-source
archive and are checked against its pinned upstream manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import struct
import sys
import zipfile

from check_mcm_contract import Report, _parse_skyrim_pex_envelope, _strip_papyrus_comment


PROJECT = "OpenMCM MCM Bridge Add-on"
BRIDGE_VERSION = "1.1.0"
BRIDGE_COMMIT = "c039e67e9455ab9b21ba3024d8f6b3b157a511e2"
GPL_SHA256 = "F817886EE6BB65ED3098A7987B1E9781653D15C71F85589CE0D2AF663C66D373"
MAX_MEMBER_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_MEMBERS = 512
BASE_FUNCTIONS = (
    "BindOption", "BindStateOption", "GetOptionID", "GetPageToken", "IsPageTokenValid",
    "SetOptionLabel", "SetOptionText", "SetOptionHelp", "SetLiveInfoText", "SetCurrentPage",
    "SetOptionsEnabled", "AddNamedHeader", "AddNamedText", "AddNamedToggle", "AddNamedSlider",
    "AddNamedMenu", "AddNamedColor", "AddNamedKeyMap", "AddNamedInput", "BridgeAddOption",
)
SCRIPTS = {
    "OpenMCM": ("", ("GetAPIVersion", "GetHostAPIVersion", "HasCapability", "IsAPIEnabled")),
    "OpenMCM_ConfigBase": ("SKI_ConfigBase", BASE_FUNCTIONS),
}
RUNTIME_FILES = frozenset(
    name for script in SCRIPTS
    for name in (f"Data/Scripts/{script}.pex", f"Data/Source/Scripts/{script}.psc")
)
ROOT_FILES = frozenset(("README.md", "LICENSE.txt", "THIRD_PARTY_NOTICES.md",
                        "OpenMCM_BRIDGE_ADDON.json", "SHA256SUMS.txt"))
UPSTREAM_FILES = frozenset((
    "LICENSE", "THIRD_PARTY_NOTICES.md", "scripts/Source/MCMBridgeNative.psc",
    "scripts/Source/host/MCMBridgeRegistry.psc", "scripts/Source/host/SKI_ConfigBase.psc",
    "scripts/Source/host/SKI_ConfigManager.psc", "scripts/Source/host/SKI_QuestBase.psc",
    "scripts/Source/host/SKI_PlayerLoadGameAlias.psc",
))
SOURCE_FILES = frozenset((
    "LICENSE.txt", "SHA256SUMS.txt",
    "src/compat/mcm-bridge/OpenMCM.psc", "src/compat/mcm-bridge/OpenMCM_ConfigBase.psc",
    "src/compat/mcm-bridge/README.md", "src/compat/mcm-bridge/THIRD_PARTY_NOTICES.md",
    "src/compat/mcm-bridge/upstream.json", "src/papyrus/OpenMCM.psc",
    "src/papyrus/OpenMCM_ConfigBase.psc", "scripts/Build-MCMBridgeAddon.ps1",
    "tools/check_mcm_bridge_addon.py", "tools/check_mcm_contract.py",
    "tools/sanitize_papyrus_metadata.py", "tools/repair_papyrus_identifiers.py",
    "tests/test_bridge_addon_package.py", "tests/test_bridge_sdk.py",
    "tests/test_bridge_addon_build.py",
    "vendor/papyrus-stubs/TESV_Papyrus_Flags.flg",
    "src/compat/mcm-bridge/compile-imports/Math.psc", "licenses/OpenMCM-previous-MIT.txt",
)) | frozenset(f"upstream/mcm-bridge/{name}" for name in UPSTREAM_FILES)
FORBIDDEN_SYMBOLS = frozenset(name.casefold() for name in (
    "SKI_ConfigManager", "OpenMCM_GetConfigID", "OpenMCM_ClearOptionState",
    "IsOpenMCMAPIEnabled", "SetOpenMCMAPIEnabled", "openMCMApiEnabled",
    "openMCMProviderID", "openMCMPageToken", "openMCMPageIndex",
    "openMCMSetOptionLabel", "openMCMSetOptionTextValue", "openMCMSetInfoText",
    "openMCMSetHighlightText", "openMCMRequestPage", "openMCMSetOptionsEnabled", "UI",
))


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _safe_name(name: str) -> None:
    if not name or "\\" in name or name.startswith("/"):
        raise ValueError(f"Unsafe archive path: {name!r}")
    reserved = {"con", "prn", "aux", "nul"} | {f"{prefix}{n}" for prefix in ("com", "lpt") for n in range(1, 10)}
    for part in name.split("/"):
        if (not part or part in (".", "..") or part.endswith((".", " ")) or
                any(ord(char) < 32 or char in ':<>"|?*' for char in part) or
                part.split(".", 1)[0].casefold() in reserved):
            raise ValueError(f"Unsafe archive path: {name!r}")


def _read_zip(raw: bytes) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    seen: set[str] = set()
    total = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if len(archive.infolist()) > MAX_MEMBERS:
            raise ValueError("Archive has too many entries")
        for member in archive.infolist():
            # ZipInfo normalizes backslashes on Windows; validate the raw name too.
            raw_name = member.orig_filename.rstrip("/") if member.is_dir() else member.orig_filename
            _safe_name(raw_name)
            name = member.filename.rstrip("/") if member.is_dir() else member.filename
            _safe_name(name)
            folded = name.casefold()
            if folded in seen:
                raise ValueError(f"Duplicate archive path: {name}")
            seen.add(folded)
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"Archive contains a link: {name}")
            if member.flag_bits & 1:
                raise ValueError(f"Encrypted archive member: {name}")
            if member.is_dir():
                continue
            if member.file_size > MAX_MEMBER_BYTES:
                raise ValueError(f"Archive member exceeds size limit: {name}")
            total += member.file_size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("Archive exceeds expanded size limit")
            files[name] = archive.read(member)
    return files


def _read_target(target: Path) -> dict[str, bytes]:
    if target.is_file():
        if target.stat().st_size > MAX_TOTAL_BYTES:
            raise ValueError("Archive exceeds input size limit")
        return _read_zip(target.read_bytes())
    if not target.is_dir() or target.is_symlink():
        raise ValueError("Target must be a ZIP or regular package directory")
    files = {}
    seen = set()
    total = 0
    for path in target.rglob("*"):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError(f"Package contains a link: {path.name}")
        if not path.is_file():
            continue
        name = path.relative_to(target).as_posix()
        _safe_name(name)
        if name.casefold() in seen:
            raise ValueError(f"Duplicate archive path: {name}")
        seen.add(name.casefold())
        size = path.stat().st_size
        total += size
        if size > MAX_MEMBER_BYTES or total > MAX_TOTAL_BYTES or len(seen) > MAX_MEMBERS:
            raise ValueError("Package exceeds size/count limit")
        files[name] = path.read_bytes()
    return files


def _manifest(files: dict[str, bytes], report: Report, scope: str) -> None:
    raw = files.get("SHA256SUMS.txt")
    if not report.check(raw is not None, f"{scope}_MANIFEST_MISSING"):
        return
    try:
        entries = {}
        seen = set()
        for line in raw.decode("utf-8-sig").splitlines():
            match = re.fullmatch(r"([0-9A-Fa-f]{64})  (.+)", line)
            if not match:
                raise ValueError("Malformed checksum line")
            digest, name = match.groups()
            _safe_name(name)
            if name.casefold() in seen or name == "SHA256SUMS.txt":
                raise ValueError("Duplicate or self-referencing checksum entry")
            seen.add(name.casefold())
            entries[name] = digest.upper()
        report.check(set(entries) == set(files) - {"SHA256SUMS.txt"}, f"{scope}_MANIFEST_INVENTORY")
        for name, digest in entries.items():
            report.check(name in files and _digest(files[name]) == digest, f"{scope}_CHECKSUM: {name}")
    except (ValueError, UnicodeError) as error:
        report.check(False, f"{scope}_MANIFEST_INVALID: {error}")


def _gpl(raw: bytes | None, report: Report, scope: str) -> None:
    # Match the full approved GPL text, permitting Windows/Unix newlines only.
    normalized = raw.replace(b"\r\n", b"\n") if raw is not None else b""
    report.check(_digest(normalized) == GPL_SHA256, f"{scope}_GPL_FULL_TEXT")


def _first_parent(blob: bytes, strings: list[str]) -> str:
    # The envelope validator has already bounded every header/table/block.
    offset = 16

    def u16() -> int:
        nonlocal offset
        value = struct.unpack_from(">H", blob, offset)[0]
        offset += 2
        return value

    for _ in range(3):
        length = u16()
        offset += length
    for _ in range(u16()):
        length = u16()
        offset += length
    has_debug = blob[offset]
    offset += 1
    if has_debug:
        offset += 8
        for _ in range(u16()):
            offset += 7
            line_count = u16()
            offset += line_count * 2
    flag_count = u16()
    offset += flag_count * 3
    if u16() != 1:
        raise ValueError("Exactly one PEX object required")
    offset += 6
    parent_index = u16()
    if parent_index >= len(strings):
        raise ValueError("Invalid parent string index")
    return strings[parent_index]


def _validate_scripts(files: dict[str, bytes], report: Report) -> None:
    for script, (parent, methods) in SCRIPTS.items():
        blob = files.get(f"Data/Scripts/{script}.pex")
        if blob is not None:
            try:
                strings, objects = _parse_skyrim_pex_envelope(blob)
                report.check(objects == [script], f"PEX_OBJECT: {script}")
                report.check(_first_parent(blob, strings) == parent, f"PEX_PARENT: {script}")
                for symbol in (script, parent, *methods):
                    if symbol:
                        report.check(symbol in strings, f"PEX_SYMBOL: {script}.{symbol}")
                for symbol in strings:
                    report.check(symbol.casefold() not in FORBIDDEN_SYMBOLS and
                                 not symbol.casefold().startswith("_root."),
                                 f"PEX_HOST_DEPENDENCY: {script}.{symbol}")
            except (ValueError, UnicodeError, struct.error) as error:
                report.check(False, f"PEX_INVALID: {script}: {error}")
        raw = files.get(f"Data/Source/Scripts/{script}.psc")
        if raw is None:
            continue
        try:
            text = "\n".join(_strip_papyrus_comment(line) for line in raw.decode("utf-8-sig").splitlines())
            identity = re.search(r"(?im)^\s*scriptname\s+(\w+)(?:\s+extends\s+(\w+))?", text)
            report.check(bool(identity and identity.group(1) == script and
                              (identity.group(2) or "") == parent), f"PSC_IDENTITY: {script}")
            for method in methods:
                report.check(re.search(rf"(?im)^\s*(?:\w+\s+)?function\s+{method}\s*\(", text)
                             is not None, f"PSC_SYMBOL: {script}.{method}")
            for symbol in re.findall(r"[A-Za-z_]\w*", text):
                report.check(symbol.casefold() not in FORBIDDEN_SYMBOLS, f"PSC_HOST_DEPENDENCY: {script}.{symbol}")
            report.check("_root." not in text.casefold(), f"PSC_HOST_DEPENDENCY: {script}.UI path")
        except UnicodeError as error:
            report.check(False, f"PSC_INVALID: {script}: {error}")


def _validate_source(raw: bytes, files: dict[str, bytes], report: Report) -> None:
    source = _read_zip(raw)
    for name in SOURCE_FILES:
        report.check(name in source, f"SOURCE_MISSING: {name}")
    _manifest(source, report, "SOURCE")
    _gpl(source.get("LICENSE.txt"), report, "SOURCE")
    report.check(any(name.startswith("vendor/papyrus-stubs/") and name.endswith(".psc")
                     for name in source), "SOURCE_COMPILE_IMPORTS_MISSING")
    for name, contents in source.items():
        allowed = (name in SOURCE_FILES or name in {"README.md", "BUILD-SOURCE.txt"} or
                   (name.startswith("vendor/papyrus-stubs/") and
                    Path(name).suffix.casefold() in {".psc", ".flg", ".md", ".txt"}))
        report.check(allowed, f"SOURCE_UNEXPECTED: {name}")
        try:
            decoded = contents.decode("utf-8-sig")
            report.check("\0" not in decoded and not contents.startswith((b"MZ", b"PK\x03\x04")),
                         f"SOURCE_NOT_TEXT: {name}")
        except UnicodeError:
            report.check(False, f"SOURCE_NOT_TEXT: {name}")
    for script in SCRIPTS:
        name = f"src/compat/mcm-bridge/{script}.psc"
        report.check(source.get(name) == files.get(f"Data/Source/Scripts/{script}.psc"),
                     f"SOURCE_RUNTIME_MISMATCH: {script}")
    for name in ("README.md", "THIRD_PARTY_NOTICES.md"):
        report.check(source.get(f"src/compat/mcm-bridge/{name}") == files.get(name),
                     f"SOURCE_DOCUMENT_MISMATCH: {name}")
    try:
        pin = json.loads(source.get("src/compat/mcm-bridge/upstream.json", b"{}"))
        report.check(pin.get("commit") == BRIDGE_COMMIT and pin.get("version") == BRIDGE_VERSION,
                     "SOURCE_UPSTREAM_IDENTITY")
        hashes = pin.get("files", {})
        if not report.check(isinstance(hashes, dict) and set(hashes) == UPSTREAM_FILES,
                            "SOURCE_UPSTREAM_PIN_INVENTORY"):
            return
        for name, digest in hashes.items():
            blob = source.get(f"upstream/mcm-bridge/{name}")
            report.check(isinstance(digest, str) and blob is not None and
                         _digest(blob) == digest.upper(), f"SOURCE_UPSTREAM_HASH: {name}")
    except (ValueError, TypeError, AttributeError) as error:
        report.check(False, f"SOURCE_UPSTREAM_INVALID: {error}")


def validate_package(target: str | Path) -> Report:
    target = Path(target)
    report = Report(str(target.resolve()), "mcm-bridge-addon-basic")
    try:
        files = _read_target(target)
        metadata = json.loads(files.get("OpenMCM_BRIDGE_ADDON.json", b"{}"))
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be an object")
        expected = {"project": PROJECT, "openMCMApiVersion": 1, "host": "MCM Bridge",
                    "bridgeVersion": BRIDGE_VERSION, "bridgeCommit": BRIDGE_COMMIT,
                    "capabilities": ["named_options"], "apiEnabled": False, "inGameVerified": False}
        for key, value in expected.items():
            report.check(type(metadata.get(key)) is type(value) and metadata.get(key) == value,
                         f"METADATA_VALUE: {key}")
        report.check(set(metadata) == set(expected) | {"version", "sourceArchive", "sourceSha256"},
                     "METADATA_FIELDS")
        version = metadata.get("version", "")
        if not report.check(isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version)
                            is not None, "METADATA_VERSION"):
            return report
        archive = f"source/OpenMCM-MCM-Bridge-Addon-{version}-Source.zip"
        report.check(metadata.get("sourceArchive") == archive, "METADATA_SOURCE_PATH")
        expected_files = ROOT_FILES | RUNTIME_FILES | {archive}
        for name in expected_files - set(files):
            report.check(False, f"PACKAGE_MISSING: {name}")
        for name in set(files) - expected_files:
            report.check(False, f"PACKAGE_UNEXPECTED: {name}")
        _manifest(files, report, "PACKAGE")
        _gpl(files.get("LICENSE.txt"), report, "PACKAGE")
        for name in ("README.md", "THIRD_PARTY_NOTICES.md"):
            raw = files.get(name, b"")
            report.check(bool(raw.strip()), f"PACKAGE_NOTICE_MISSING: {name}")
        _validate_scripts(files, report)
        raw = files.get(archive)
        if raw is not None:
            report.check(metadata.get("sourceSha256") == _digest(raw), "SOURCE_ARCHIVE_HASH")
            _validate_source(raw, files, report)
    except (OSError, ValueError, TypeError, UnicodeError, zipfile.BadZipFile, RuntimeError) as error:
        report.check(False, f"PACKAGE_INVALID: {error}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    args = parser.parse_args(argv)
    report = validate_package(args.target)
    for error in report.errors:
        print(f"ERROR: {error}")
    print(f"{'PASS' if report.ok else 'FAIL'}: {report.checks} BASIC Bridge add-on package checks")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
