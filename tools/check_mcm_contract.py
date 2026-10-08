#!/usr/bin/env python3
"""Static compatibility checks for the standalone SkyUI-style MCM package.

The checker deliberately uses only Python's standard library.  It can inspect a
source checkout, an unpacked release, or a release zip without launching Skyrim.
The compatibility surface lives in ``tests/contracts/skyui6_mcm_contract.json``
so changes to the contract are reviewable data rather than hidden in test code.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import struct
import sys
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable, Iterator, Sequence


PEX_MAGIC = bytes.fromhex("fa57c0de")
SWF_MAGICS = (b"FWS", b"CWS", b"ZWS")
# Checkout caches and generated/staged copies are not implementation sources.
# Keep this separate from release inventories: a packaged cache file must still
# be included in exact checksum/unsafe-path checks rather than silently hidden.
SOURCE_IGNORED_ROOTS = frozenset((".tools", "build", "dist", "vendor"))


@dataclass(frozen=True)
class Entry:
    """One file exposed by a directory or zip package."""

    name: str
    key: str


class PackageView:
    """Case-insensitive, read-only view over a directory or zip archive."""

    def __init__(self, target: Path, *, source_only: bool = False):
        self.target = target.resolve()
        self._zip: zipfile.ZipFile | None = None
        self._disk_paths: dict[str, Path] = {}
        self._entries: dict[str, Entry] = {}

        if self.target.is_dir():
            for directory, directories, filenames in os.walk(self.target):
                directory_path = Path(directory)
                if source_only and directory_path == self.target:
                    directories[:] = [
                        name for name in directories
                        if name.casefold() not in SOURCE_IGNORED_ROOTS
                    ]
                for filename in filenames:
                    path = directory_path / filename
                    if not path.is_file():
                        continue
                    rel = path.relative_to(self.target).as_posix()
                    key = self._key(rel)
                    self._entries.setdefault(key, Entry(rel, key))
                    self._disk_paths.setdefault(key, path)
        elif self.target.is_file() and zipfile.is_zipfile(self.target):
            self._zip = zipfile.ZipFile(self.target)
            try:
                for info in self._zip.infolist():
                    raw_name = info.filename
                    normalized = raw_name.replace("\\", "/")
                    # ZIP directory entries conventionally end in '/'. Remove
                    # that one marker before applying the same traversal and
                    # absolute-path checks used for file entries.
                    checked_name = (
                        normalized[:-1]
                        if info.is_dir() and normalized.endswith("/")
                        else normalized
                    )
                    parts = checked_name.split("/")
                    if (
                        not checked_name
                        or "\\" in raw_name
                        or checked_name.startswith("/")
                        or re.match(r"^[A-Za-z]:", checked_name)
                        or any(part in ("", ".", "..") for part in parts)
                    ):
                        raise ValueError(f"unsafe zip entry path: {raw_name!r}")
                    if info.is_dir():
                        continue
                    name = self._clean(checked_name)
                    key = self._key(name)
                    if key in self._entries:
                        raise ValueError(f"duplicate zip entry path: {raw_name!r}")
                    self._entries[key] = Entry(name, key)
            except Exception:
                self._zip.close()
                self._zip = None
                raise
        else:
            raise ValueError(f"target is not a directory or zip archive: {target}")

    @staticmethod
    def _clean(value: str) -> str:
        value = value.replace("\\", "/")
        while value.startswith("./"):
            value = value[2:]
        return value

    @classmethod
    def _key(cls, value: str) -> str:
        return cls._clean(value).casefold()

    @property
    def entries(self) -> Sequence[Entry]:
        return tuple(self._entries.values())

    def get(self, path: str) -> Entry | None:
        return self._entries.get(self._key(path))

    def get_data_path(self, path: str) -> Entry | None:
        """Resolve a path relative to either package root or its Data folder."""

        clean = self._clean(path)
        return self.get(clean) or self.get(f"Data/{clean}")

    def glob(self, patterns: Iterable[str], *, source_only: bool = False) -> list[Entry]:
        patterns_cf = [self._key(pattern) for pattern in patterns]
        matches: list[Entry] = []
        for entry in self._entries.values():
            if source_only and entry.key.split("/", 1)[0] in SOURCE_IGNORED_ROOTS:
                continue
            for pattern in patterns_cf:
                if fnmatch.fnmatchcase(entry.key, pattern):
                    matches.append(entry)
                    break
                if pattern.startswith("**/") and fnmatch.fnmatchcase(
                    PurePosixPath(entry.key).name, pattern[3:]
                ):
                    matches.append(entry)
                    break
        return sorted(matches, key=lambda item: item.key)

    def read_bytes(self, entry: Entry) -> bytes:
        if self._zip is not None:
            return self._zip.read(entry.name)
        return self._disk_paths[entry.key].read_bytes()

    def read_text(self, entry: Entry) -> str:
        raw = self.read_bytes(entry)
        for encoding in ("utf-8-sig", "utf-8", "cp1252"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                pass
        return raw.decode("latin-1")

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    @property
    def is_zip(self) -> bool:
        return self._zip is not None

    def __enter__(self) -> "PackageView":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


@dataclass
class Report:
    target: str
    profile: str
    checks: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def check(self, condition: bool, message: str) -> bool:
        self.checks += 1
        if not condition:
            self.errors.append(message)
        return condition

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "target": self.target,
            "profile": self.profile,
            "checks": self.checks,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _strip_papyrus_comment(line: str) -> str:
    quoted = False
    escaped = False
    for index, char in enumerate(line):
        if char == '"' and not escaped:
            quoted = not quoted
        if char == ";" and not quoted:
            return line[:index]
        escaped = char == "\\" and not escaped
        if char != "\\":
            escaped = False
    return line


def normalize_declaration(value: str) -> str:
    """Normalize a one-line Papyrus declaration without weakening its signature."""

    value = _strip_papyrus_comment(value).strip().casefold()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s*\(\s*", "(", value)
    value = re.sub(r"\s*\)\s*", ")", value)
    value = re.sub(r"\s*,\s*", ",", value)
    value = re.sub(r"\s*=\s*", "=", value)
    return value


def papyrus_declarations(text: str) -> set[str]:
    declarations: set[str] = set()
    for line in text.splitlines():
        code = _strip_papyrus_comment(line).strip()
        if re.match(
            r"(?i)^(?:(?:bool|float|form|int|string|\w+(?:\[\])?)\s+)?"
            r"(?:event|function)\b",
            code,
        ) or re.match(r"(?i)^\w+(?:\[\])?\s+property\b", code):
            declarations.add(normalize_declaration(code))
    return declarations


def declaration_symbol(declaration: str) -> str | None:
    match = re.search(r"(?i)\b(?:event|function|property)\s+(\w+)", declaration)
    return match.group(1) if match else None


def contains_symbol(text: str, symbol: str) -> bool:
    return re.search(rf"(?i)(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])", text) is not None


def _best_source_candidate(
    view: PackageView, candidates: Sequence[Entry], contract: dict[str, object]
) -> tuple[Entry, str] | None:
    """Choose the implementation source when SDK headers with the same name exist."""

    best: tuple[int, Entry, str] | None = None
    required_declarations = contract.get("required_declarations", [])
    required_identifiers = contract.get("required_identifiers", [])
    required_literals = contract.get("required_literals", [])
    for entry in candidates:
        text = view.read_text(entry)
        declarations = papyrus_declarations(text)
        score = sum(
            normalize_declaration(item) in declarations
            for item in required_declarations  # type: ignore[union-attr]
        )
        score += sum(
            contains_symbol(text, item)
            for item in required_identifiers  # type: ignore[union-attr]
        )
        score += sum(item in text for item in required_literals)  # type: ignore[union-attr]
        candidate = (score, entry, text)
        if best is None or candidate[0] > best[0]:
            best = candidate
    return (best[1], best[2]) if best else None


def _validate_papyrus_source(
    view: PackageView,
    report: Report,
    contract: dict[str, object],
) -> None:
    script = str(contract["script"])
    candidates = view.glob(contract["source_globs"], source_only=True)  # type: ignore[arg-type]
    if not report.check(bool(candidates), f"PAPYRUS_SOURCE_MISSING: {script}.psc not found"):
        return
    selected = _best_source_candidate(view, candidates, contract)
    assert selected is not None
    entry, text = selected

    expected_base = contract.get("extends")
    header = re.search(
        rf"(?im)^\s*scriptname\s+{re.escape(script)}"
        + (rf"\s+extends\s+{re.escape(str(expected_base))}\b" if expected_base else r"\b"),
        text,
    )
    report.check(
        header is not None,
        f"PAPYRUS_BASE_MISMATCH: {entry.name} must declare {script}"
        + (f" extends {expected_base}" if expected_base else ""),
    )

    actual_declarations = papyrus_declarations(text)
    for declaration in contract.get("required_declarations", []):  # type: ignore[union-attr]
        report.check(
            normalize_declaration(declaration) in actual_declarations,
            f"PAPYRUS_SIGNATURE_MISSING: {entry.name}: {declaration}",
        )
    for identifier in contract.get("required_identifiers", []):  # type: ignore[union-attr]
        report.check(
            contains_symbol(text, identifier),
            f"MCM_HELPER_FIELD_MISSING: {entry.name}: {identifier}",
        )
    for literal in contract.get("required_literals", []):  # type: ignore[union-attr]
        report.check(
            literal in text,
            f"PAPYRUS_LITERAL_MISSING: {entry.name}: {literal}",
        )
    for requirement in contract.get("required_patterns", []):  # type: ignore[union-attr]
        pattern = requirement["pattern"]
        description = requirement.get("description", pattern)
        report.check(
            re.search(pattern, text) is not None,
            f"PAPYRUS_LAYOUT_MISMATCH: {entry.name}: {description}",
        )
    for binding in contract.get("required_event_bindings", []):  # type: ignore[union-attr]
        event_name = re.escape(binding["event"])
        handler = re.escape(binding["handler"])
        pattern = (
            rf'(?is)\b(?:(?i:self)\s*\.\s*)?(?i:RegisterForModEvent)\s*\('
            rf'\s*"{event_name}"\s*,\s*"{handler}"\s*\)'
        )
        report.check(
            re.search(pattern, text) is not None,
            f"PAPYRUS_EVENT_BINDING_MISSING: {entry.name}: "
            f"{binding['event']} -> {binding['handler']}",
        )
    for event_name_raw in contract.get("required_sent_events", []):  # type: ignore[union-attr]
        event_name = re.escape(event_name_raw)
        pattern = rf'(?is)\b(?i:SendModEvent)\s*\(\s*"{event_name}"(?:\s*[,\)])'
        report.check(
            re.search(pattern, text) is not None,
            f"PAPYRUS_EVENT_SEND_MISSING: {entry.name}: {event_name_raw}",
        )


def _validate_pex(
    view: PackageView,
    report: Report,
    contract: dict[str, object],
) -> None:
    script = str(contract["script"])
    path = f"Scripts/{script}.pex"
    entry = view.get_data_path(path)
    if not report.check(entry is not None, f"RUNTIME_PATH_MISSING: Data/{path}"):
        return
    assert entry is not None
    blob = view.read_bytes(entry)
    try:
        strings, object_names = _parse_skyrim_pex_envelope(blob)
    except (UnicodeDecodeError, ValueError, struct.error) as exc:
        report.check(False, f"PEX_PARSE_ERROR: {entry.name}: {exc}")
        return
    report.check(
        script.casefold() in {name.casefold() for name in object_names},
        f"PEX_OBJECT_MISSING: {entry.name}: {script}",
    )
    exact_string_symbols = set(strings)
    for identifier in contract.get("required_exact_identifiers", []):  # type: ignore[union-attr]
        report.check(
            identifier in exact_string_symbols,
            f"PEX_EXACT_IDENTIFIER_MISSING: {entry.name}: {identifier}",
        )
    for identifier in contract.get("forbidden_identifiers", []):  # type: ignore[union-attr]
        report.check(
            identifier not in exact_string_symbols,
            f"PEX_FORBIDDEN_IDENTIFIER: {entry.name}: {identifier}",
        )
    string_symbols = {value.casefold() for value in strings}
    symbols = set(contract.get("required_identifiers", []))
    symbols.update(
        symbol
        for declaration in contract.get("required_declarations", [])  # type: ignore[union-attr]
        if (symbol := declaration_symbol(declaration)) is not None
    )
    symbols.update((script, str(contract.get("extends", ""))))
    for symbol in sorted(symbols, key=str.casefold):
        if not symbol:
            continue
        report.check(
            symbol.casefold() in string_symbols,
            f"PEX_SYMBOL_MISSING: {entry.name}: {symbol}",
        )


def _parse_skyrim_pex_envelope(blob: bytes) -> tuple[list[str], list[str]]:
    """Parse the bounded Skyrim PEX envelope, tables, and object blocks.

    The object payloads are compiler bytecode and are skipped using their
    encoded block sizes. This still proves that symbols come from a coherent
    Skyrim PEX string table instead of an arbitrary blob with a magic prefix.
    """

    offset = 0

    def take(size: int) -> bytes:
        nonlocal offset
        if size < 0 or offset + size > len(blob):
            raise ValueError(f"truncated data at byte {offset}")
        value = blob[offset : offset + size]
        offset += size
        return value

    def u8() -> int:
        return take(1)[0]

    def u16() -> int:
        return struct.unpack(">H", take(2))[0]

    def u64() -> int:
        return struct.unpack(">Q", take(8))[0]

    def pex_string() -> str:
        length = u16()
        return take(length).decode("utf-8")

    if take(4) != PEX_MAGIC:
        raise ValueError("invalid Papyrus magic")
    major, minor, game_id = u8(), u8(), u16()
    if (major, minor, game_id) != (3, 2, 1):
        raise ValueError(
            f"unexpected Skyrim PEX version/game tuple {major}.{minor}/{game_id}"
        )
    u64()  # compilation timestamp
    pex_string()  # source path
    pex_string()  # compiler user
    pex_string()  # compiler machine

    string_count = u16()
    strings = [pex_string() for _ in range(string_count)]
    if not strings:
        raise ValueError("empty PEX string table")

    has_debug = u8()
    if has_debug not in (0, 1):
        raise ValueError(f"invalid debug-info flag {has_debug}")
    if has_debug:
        u64()
        function_count = u16()
        for _ in range(function_count):
            refs = (u16(), u16(), u16())
            if any(ref >= string_count for ref in refs):
                raise ValueError("debug function uses an invalid string index")
            u8()
            line_count = u16()
            take(line_count * 2)

    user_flag_count = u16()
    for _ in range(user_flag_count):
        if u16() >= string_count:
            raise ValueError("user flag uses an invalid string index")
        u8()

    object_count = u16()
    if object_count < 1:
        raise ValueError("PEX contains no script objects")
    object_names: list[str] = []
    for _ in range(object_count):
        name_index = u16()
        if name_index >= string_count:
            raise ValueError("script object uses an invalid name index")
        object_names.append(strings[name_index])
        # Skyrim PEX stores this block-size field little-endian even though
        # its other integers are big-endian.
        object_size = struct.unpack("<I", take(4))[0]
        if object_size < 16:
            raise ValueError(f"invalid script object size {object_size}")
        take(object_size)

    if offset != len(blob):
        raise ValueError(f"{len(blob) - offset} trailing byte(s)")
    return strings, object_names


def _searchable_swf(blob: bytes) -> bytes:
    if len(blob) < 8 or blob[:3] not in SWF_MAGICS:
        raise ValueError("not a SWF file")
    declared_size = struct.unpack_from("<I", blob, 4)[0]
    if blob[:3] == b"CWS":
        decoded = b"FWS" + blob[3:8] + zlib.decompress(blob[8:])
    elif blob[:3] == b"FWS":
        decoded = blob
    else:
        raise ValueError("LZMA-compressed ZWS is unsupported by the contract checker")
    if len(decoded) != declared_size:
        raise ValueError(
            f"declared uncompressed size {declared_size} does not match {len(decoded)}"
        )

    # Validate the frame header and every tag boundary through the mandatory
    # End tag. Tokens are searched only after this structural pass succeeds.
    nbits = decoded[8] >> 3
    rect_size = (5 + nbits * 4 + 7) // 8
    offset = 8 + rect_size
    if offset + 4 > len(decoded):
        raise ValueError("truncated SWF frame header")
    offset += 4  # frame rate and frame count
    saw_end = False
    while offset + 2 <= len(decoded):
        tag_header = struct.unpack_from("<H", decoded, offset)[0]
        offset += 2
        tag_code = tag_header >> 6
        tag_size = tag_header & 0x3F
        if tag_size == 0x3F:
            if offset + 4 > len(decoded):
                raise ValueError("truncated long SWF tag header")
            tag_size = struct.unpack_from("<I", decoded, offset)[0]
            offset += 4
        if offset + tag_size > len(decoded):
            raise ValueError(f"truncated SWF tag {tag_code}")
        offset += tag_size
        if tag_code == 0:
            if tag_size != 0:
                raise ValueError("invalid SWF End tag")
            saw_end = True
            break
    if not saw_end:
        raise ValueError("SWF has no End tag")
    if offset != len(decoded):
        raise ValueError(f"SWF has {len(decoded) - offset} trailing byte(s)")
    return decoded


def _validate_token_asset(
    view: PackageView,
    report: Report,
    asset: dict[str, object],
    profile: str,
) -> None:
    label = str(asset["name"])
    required_tokens = asset.get(f"required_{profile}_tokens", asset.get("required_tokens", []))
    if profile == "source":
        candidates = view.glob(asset["source_globs"], source_only=True)  # type: ignore[arg-type]
        if not report.check(bool(candidates), f"UI_SOURCE_MISSING: {label}"):
            return
        # AS sources can be split; the bridge contract is satisfied by their union.
        corpus = "\n".join(view.read_text(entry) for entry in candidates)
        location = ", ".join(entry.name for entry in candidates)
        for token in required_tokens:  # type: ignore[union-attr]
            report.check(
                token in corpus,
                f"UI_TOKEN_MISSING: {location}: {token}",
            )
        for requirement in asset.get("required_source_patterns", []):  # type: ignore[union-attr]
            pattern = requirement["pattern"]
            description = requirement.get("description", pattern)
            report.check(
                re.search(pattern, corpus) is not None,
                f"UI_LAYOUT_MISMATCH: {location}: {description}",
            )
        for event_name_raw in asset.get("required_dispatched_events", []):  # type: ignore[union-attr]
            event_name = re.escape(event_name_raw)
            pattern = (
                rf'(?s)(?:[A-Za-z_$][\w$]*\s*\.\s*)?'
                rf'(?i:SendModEvent)\s*\(\s*"{event_name}"(?:\s*[,\)])'
            )
            report.check(
                re.search(pattern, corpus) is not None,
                f"UI_EVENT_DISPATCH_MISSING: {location}: {event_name_raw}",
            )
        return

    runtime_path = str(asset["runtime_path"])
    entry = view.get_data_path(runtime_path)
    if not report.check(entry is not None, f"RUNTIME_PATH_MISSING: Data/{runtime_path}"):
        return
    assert entry is not None
    blob = view.read_bytes(entry)
    try:
        corpus = _searchable_swf(blob)
    except (ValueError, zlib.error) as exc:
        report.check(False, f"SWF_INVALID: {entry.name}: {exc}")
        return
    for token in required_tokens:  # type: ignore[union-attr]
        report.check(
            token.encode("utf-8") in corpus,
            f"SWF_TOKEN_MISSING: {entry.name}: {token}",
        )


def _subrecords(data: bytes) -> Iterator[tuple[bytes, bytes]]:
    offset = 0
    extended_size: int | None = None
    while offset + 6 <= len(data):
        signature = data[offset : offset + 4]
        size = struct.unpack_from("<H", data, offset + 4)[0]
        offset += 6
        if offset + size > len(data):
            raise ValueError(f"truncated {signature!r} subrecord")
        payload = data[offset : offset + size]
        offset += size
        if signature == b"XXXX":
            if len(payload) != 4:
                raise ValueError("invalid XXXX subrecord")
            extended_size = struct.unpack("<I", payload)[0]
            continue
        if extended_size is not None:
            if offset - size + extended_size > len(data):
                raise ValueError(f"truncated extended {signature!r} subrecord")
            payload = data[offset - size : offset - size + extended_size]
            offset = offset - size + extended_size
            extended_size = None
        yield signature, payload


def _plugin_records(blob: bytes) -> Iterator[tuple[bytes, int, int, bytes]]:
    def walk(start: int, end: int) -> Iterator[tuple[bytes, int, int, bytes]]:
        offset = start
        while offset + 24 <= end:
            signature = blob[offset : offset + 4]
            size = struct.unpack_from("<I", blob, offset + 4)[0]
            if signature == b"GRUP":
                if size < 24 or offset + size > end:
                    raise ValueError("invalid GRUP size")
                yield from walk(offset + 24, offset + size)
                offset += size
                continue
            record_end = offset + 24 + size
            if record_end > end:
                raise ValueError(f"truncated {signature!r} record")
            form_id = struct.unpack_from("<I", blob, offset + 12)[0]
            flags = struct.unpack_from("<I", blob, offset + 8)[0]
            data = blob[offset + 24 : record_end]
            if flags & 0x00040000:
                if len(data) < 4:
                    raise ValueError("truncated compressed record")
                data = zlib.decompress(data[4:])
            yield signature, form_id, flags, data
            offset = record_end
        if offset != end:
            raise ValueError("trailing or truncated plugin bytes")

    yield from walk(0, len(blob))


def _decode_zstring(value: bytes) -> str:
    return value.rstrip(b"\0").decode("utf-8", errors="replace")


def _validate_checksum_manifest(
    view: PackageView, report: Report, *, required: bool = False
) -> None:
    """Validate an exact package inventory and optionally require its manifest."""

    manifest_entry = view.get("OpenMCM_SHA256SUMS.txt")
    if manifest_entry is None:
        if required:
            report.check(
                False,
                "CHECKSUM_MANIFEST_MISSING: release ZIP must contain "
                "OpenMCM_SHA256SUMS.txt",
            )
        return

    expected: dict[str, tuple[str, str]] = {}
    for line_number, raw_line in enumerate(view.read_text(manifest_entry).splitlines(), 1):
        if not raw_line.strip():
            continue
        match = re.fullmatch(r"([0-9A-Fa-f]{64})  ([^\r\n]+)", raw_line)
        if not report.check(
            match is not None,
            f"CHECKSUM_MANIFEST_INVALID: line {line_number} has invalid syntax",
        ):
            continue
        assert match is not None
        digest, name = match.groups()
        normalized = PackageView._clean(name)
        key = PackageView._key(normalized)
        report.check(
            key != manifest_entry.key,
            "CHECKSUM_MANIFEST_INVALID: the checksum manifest cannot list itself",
        )
        if not report.check(
            key not in expected,
            f"CHECKSUM_MANIFEST_DUPLICATE: {normalized}",
        ):
            continue
        expected[key] = (normalized, digest.casefold())

    actual_keys = {entry.key for entry in view.entries if entry.key != manifest_entry.key}
    expected_keys = set(expected)
    for key in sorted(expected_keys - actual_keys):
        report.check(False, f"CHECKSUM_FILE_MISSING: {expected[key][0]}")
    for key in sorted(actual_keys - expected_keys):
        entry = next(item for item in view.entries if item.key == key)
        report.check(False, f"CHECKSUM_FILE_UNLISTED: {entry.name}")
    report.check(
        actual_keys == expected_keys,
        "CHECKSUM_INVENTORY_MISMATCH: package contents differ from OpenMCM_SHA256SUMS.txt",
    )

    for key in sorted(actual_keys & expected_keys):
        entry = view.get(expected[key][0])
        assert entry is not None
        actual_digest = hashlib.sha256(view.read_bytes(entry)).hexdigest()
        report.check(
            actual_digest == expected[key][1],
            f"CHECKSUM_MISMATCH: {entry.name}",
        )


def _validate_plugin_binary(
    blob: bytes, entry: Entry, report: Report, identity: dict[str, object]
) -> None:
    if not report.check(blob.startswith(b"TES4"), f"PLUGIN_INVALID: {entry.name} has no TES4 header"):
        return
    try:
        records = list(_plugin_records(blob))
        tes4 = next(item for item in records if item[0] == b"TES4")
        required_plugin_flags = int(str(identity.get("plugin_record_flags_required", "0")), 0)
        report.check(
            (tes4[2] & required_plugin_flags) == required_plugin_flags,
            f"PLUGIN_FLAGS_MISMATCH: {entry.name} lacks required TES4 flags "
            f"0x{required_plugin_flags:08X}",
        )
        masters = [
            _decode_zstring(payload)
            for signature, payload in _subrecords(tes4[3])
            if signature == b"MAST"
        ]
        allowed = {str(item).casefold() for item in identity.get("allowed_masters", [])}
        for master in masters:
            report.check(
                master.casefold() in allowed,
                f"EXTERNAL_MASTER_FORBIDDEN: {entry.name} depends on {master}",
            )

        local_id = int(str(identity["manager_form_local_id"]), 0)
        quests = [
            record for record in records if record[0] == b"QUST" and (record[1] & 0x00FFFFFF) == local_id
        ]
        if not report.check(
            len(quests) == 1,
            f"MANAGER_FORM_MISSING: {entry.name} needs one QUST with local FormID 0x{local_id:06X}",
        ):
            return
        quest = quests[0]
        subrecords = list(_subrecords(quest[3]))
        editor_ids = [
            _decode_zstring(payload) for signature, payload in subrecords if signature == b"EDID"
        ]
        expected_editor = str(identity["manager_editor_id"])
        report.check(
            editor_ids == [expected_editor],
            f"MANAGER_EDITOR_ID_MISMATCH: expected {expected_editor}, found {editor_ids or 'none'}",
        )
        vmad = b"".join(payload for signature, payload in subrecords if signature == b"VMAD")
        expected_script = str(identity["manager_script"])
        report.check(
            expected_script.encode("ascii") in vmad,
            f"MANAGER_SCRIPT_MISSING: form 0x{local_id:06X} lacks {expected_script}",
        )

        required_quest_flags = int(str(identity.get("manager_quest_flags_required", "0")), 0)
        dnam_values = [payload for signature, payload in subrecords if signature == b"DNAM"]
        quest_flags = struct.unpack_from("<H", dnam_values[0])[0] if dnam_values and len(dnam_values[0]) >= 2 else 0
        report.check(
            (quest_flags & required_quest_flags) == required_quest_flags,
            f"MANAGER_QUEST_FLAGS_MISMATCH: form 0x{local_id:06X} lacks required flags "
            f"0x{required_quest_flags:04X}",
        )

        expected_stage = int(identity.get("manager_stage", 1))
        stage_indices = [
            struct.unpack_from("<H", payload)[0]
            for signature, payload in subrecords
            if signature == b"INDX" and len(payload) >= 2
        ]
        report.check(
            expected_stage in stage_indices,
            f"MANAGER_STAGE_MISSING: form 0x{local_id:06X} lacks stage {expected_stage}",
        )

        for field, label in (
            ("manager_fragment_script", "manager fragment script"),
            ("manager_fragment_name", "manager fragment function"),
            ("player_alias_property", "player alias property"),
            ("player_alias_script", "player alias script"),
        ):
            expected = str(identity[field])
            report.check(
                expected.encode("ascii") in vmad,
                f"MANAGER_VMAD_MISSING: form 0x{local_id:06X} lacks {label} {expected}",
            )

        expected_alias_id = int(identity.get("player_alias_id", 0))
        alias_starts = [
            index
            for index, (signature, payload) in enumerate(subrecords)
            if signature == b"ALST"
            and len(payload) >= 4
            and struct.unpack_from("<I", payload)[0] == expected_alias_id
        ]
        alias_segment: list[tuple[bytes, bytes]] = []
        if alias_starts:
            start = alias_starts[0]
            for signature, payload in subrecords[start + 1 :]:
                if signature in (b"ALST", b"ALED"):
                    break
                alias_segment.append((signature, payload))
        report.check(
            bool(alias_starts),
            f"PLAYER_ALIAS_MISSING: form 0x{local_id:06X} lacks alias {expected_alias_id}",
        )
        expected_alias_name = str(identity["player_alias_name"])
        alias_names = [
            _decode_zstring(payload) for signature, payload in alias_segment if signature == b"ALID"
        ]
        report.check(
            alias_names == [expected_alias_name],
            f"PLAYER_ALIAS_NAME_MISMATCH: expected {expected_alias_name}, found {alias_names or 'none'}",
        )
        expected_player_ref = int(str(identity["player_reference_form_local_id"]), 0)
        alias_refs = [
            struct.unpack_from("<I", payload)[0] & 0x00FFFFFF
            for signature, payload in alias_segment
            if signature == b"ALFR" and len(payload) >= 4
        ]
        report.check(
            alias_refs == [expected_player_ref],
            f"PLAYER_ALIAS_REFERENCE_MISMATCH: expected 0x{expected_player_ref:06X}, "
            f"found {alias_refs or 'none'}",
        )
    except (StopIteration, struct.error, ValueError, zlib.error) as exc:
        report.check(False, f"PLUGIN_PARSE_ERROR: {entry.name}: {exc}")


def _validate_plugin_source(
    view: PackageView, report: Report, identity: dict[str, object]
) -> None:
    header_candidates = view.glob(identity["source_header_globs"], source_only=True)  # type: ignore[arg-type]
    record_candidates = view.glob(identity["source_record_globs"], source_only=True)  # type: ignore[arg-type]
    if not report.check(bool(header_candidates), "PLUGIN_SOURCE_MISSING: RecordData.yaml"):
        return
    if not report.check(bool(record_candidates), "MANAGER_SOURCE_MISSING: manager quest YAML"):
        return
    header_entry = header_candidates[0]
    header = view.read_text(header_entry)
    plugin_name = str(identity["plugin_name"])
    report.check(
        re.search(rf"(?im)^\s*ModKey:\s*{re.escape(plugin_name)}\s*$", header) is not None,
        f"PLUGIN_NAME_MISMATCH: {header_entry.name} must use ModKey {plugin_name}",
    )
    allowed = {str(item).casefold() for item in identity.get("allowed_masters", [])}
    masters = re.findall(r"(?im)^\s*-?\s*Master:\s*([^\r\n#]+?)\s*$", header)
    for master in masters:
        report.check(
            master.casefold() in allowed,
            f"EXTERNAL_MASTER_FORBIDDEN: {header_entry.name} depends on {master}",
        )

    expected_id = int(str(identity["manager_form_local_id"]), 0)
    expected_editor = str(identity["manager_editor_id"])
    expected_script = str(identity["manager_script"])
    selected: tuple[Entry, str] | None = None
    for entry in record_candidates:
        text = view.read_text(entry)
        if re.search(rf"(?im)^\s*FormKey:\s*0*{expected_id:X}:{re.escape(plugin_name)}\s*$", text):
            selected = (entry, text)
            break
    if not report.check(
        selected is not None,
        f"MANAGER_FORM_MISSING: source needs local FormID 0x{expected_id:06X}",
    ):
        return
    entry, text = selected  # type: ignore[misc]
    report.check(
        re.search(rf"(?im)^\s*EditorID:\s*{re.escape(expected_editor)}\s*$", text) is not None,
        f"MANAGER_EDITOR_ID_MISMATCH: {entry.name} must use {expected_editor}",
    )
    report.check(
        re.search(rf"(?im)^\s*-\s*Name:\s*{re.escape(expected_script)}\s*$", text) is not None,
        f"MANAGER_SCRIPT_MISSING: {entry.name} must attach {expected_script}",
    )
    required_header_flag = "Small"
    report.check(
        re.search(rf"(?im)^\s*-\s*{required_header_flag}\s*$", header) is not None,
        f"PLUGIN_FLAGS_MISMATCH: {header_entry.name} must declare {required_header_flag}",
    )
    required_quest_flags = ("StartGameEnabled", "AllowRepeatedStages", "RunOnce")
    for quest_flag in required_quest_flags:
        report.check(
            re.search(rf"(?im)^\s*-\s*{re.escape(quest_flag)}\s*$", text) is not None,
            f"MANAGER_QUEST_FLAGS_MISMATCH: {entry.name} must declare {quest_flag}",
        )
    for field, yaml_key in (
        ("manager_fragment_script", "ScriptName"),
        ("manager_fragment_name", "FragmentName"),
        ("player_alias_property", "Name"),
        ("player_alias_script", "Name"),
        ("player_alias_name", "Name"),
    ):
        expected = str(identity[field])
        report.check(
            re.search(rf"(?im)^\s*(?:-\s*)?{yaml_key}:\s*{re.escape(expected)}\s*$", text)
            is not None,
            f"MANAGER_SOURCE_WIRING_MISSING: {entry.name} needs {yaml_key}: {expected}",
        )
    expected_stage = int(identity.get("manager_stage", 1))
    report.check(
        re.search(rf"(?im)^\s*-\s*Index:\s*{expected_stage}\s*$", text) is not None,
        f"MANAGER_STAGE_MISSING: {entry.name} needs stage {expected_stage}",
    )
    expected_player_ref = int(str(identity["player_reference_form_local_id"]), 0)
    report.check(
        re.search(rf"(?im)^\s*ForcedReference:\s*0*{expected_player_ref:X}:Skyrim\.esm\s*$", text)
        is not None,
        f"PLAYER_ALIAS_REFERENCE_MISMATCH: {entry.name} must force Skyrim.esm "
        f"form 0x{expected_player_ref:06X}",
    )


def _resolve_profile(view: PackageView, manifest: dict[str, object], requested: str) -> str:
    if requested != "auto":
        return requested
    runtime = manifest["runtime"]  # type: ignore[index]
    required_paths = runtime["required_data_paths"]  # type: ignore[index]
    return "release" if all(view.get_data_path(path) for path in required_paths) else "source"


def validate(
    target: str | Path,
    manifest_path: str | Path,
    profile: str = "auto",
    require_source: bool = False,
) -> Report:
    """Validate ``target`` and return all findings instead of failing fast."""

    target_path = Path(target)
    manifest_file = Path(manifest_path)
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError(f"unsupported contract schema: {manifest.get('schema_version')!r}")

    with PackageView(target_path, source_only=profile == "source") as view:
        selected_profile = _resolve_profile(view, manifest, profile)
        report = Report(str(target_path.resolve()), selected_profile)

        if selected_profile in ("release", "both"):
            _validate_checksum_manifest(view, report, required=view.is_zip)
            runtime = manifest["runtime"]
            for path in runtime["required_data_paths"]:
                report.check(
                    view.get_data_path(path) is not None,
                    f"RUNTIME_PATH_MISSING: Data/{path}",
                )

            identity = manifest["identity"]
            plugin_entry = view.get_data_path(identity["plugin_path"])
            if report.check(
                plugin_entry is not None,
                f"RUNTIME_PATH_MISSING: Data/{identity['plugin_path']}",
            ):
                assert plugin_entry is not None
                _validate_plugin_binary(view.read_bytes(plugin_entry), plugin_entry, report, identity)

            for contract in manifest["papyrus"]:
                _validate_pex(view, report, contract)
                if require_source:
                    _validate_papyrus_source(view, report, contract)
            for asset in manifest["ui_assets"]:
                _validate_token_asset(view, report, asset, "release")

        if selected_profile in ("source", "both"):
            _validate_plugin_source(view, report, manifest["identity"])
            for contract in manifest["papyrus"]:
                _validate_papyrus_source(view, report, contract)
            for asset in manifest["ui_assets"]:
                _validate_token_asset(view, report, asset, "source")

        return report


def default_manifest() -> Path:
    return Path(__file__).resolve().parents[1] / "tests" / "contracts" / "skyui6_mcm_contract.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        nargs="?",
        default=str(Path(__file__).resolve().parents[1]),
        help="source checkout, unpacked package, or release zip (default: repository root)",
    )
    parser.add_argument(
        "--manifest",
        default=str(default_manifest()),
        help="compatibility contract JSON",
    )
    parser.add_argument(
        "--profile",
        choices=("auto", "source", "release", "both"),
        default="auto",
        help="evidence to inspect; auto selects release only when all runtime files exist",
    )
    parser.add_argument(
        "--require-source",
        action="store_true",
        help="also demand exact Papyrus source signatures when checking a release",
    )
    parser.add_argument("--json", action="store_true", help="emit a machine-readable report")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = validate(args.target, args.manifest, args.profile, args.require_source)
    except (OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.as_dict(), indent=2))
    else:
        status = "PASS" if report.ok else "FAIL"
        print(f"{status}: {report.checks} static MCM contract checks ({report.profile})")
        for warning in report.warnings:
            print(f"WARN: {warning}")
        for error in report.errors:
            print(f"ERROR: {error}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
