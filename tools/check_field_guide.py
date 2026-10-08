#!/usr/bin/env python3
"""Read-only structural validation of the optional OpenMCM Field Guide package.

This validates actual ESP records, VMAD, SEQ, PEX identity and exact installable
payload. It is not an in-game test and never reads or modifies the game folder.
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
import zlib
from pathlib import Path

from check_mcm_contract import (
    PackageView, Report, _parse_skyrim_pex_envelope, _plugin_records,
    _strip_papyrus_comment, _validate_checksum_manifest, _validate_pex,
)
from check_openmcm_api import _first_parent

SCRIPT = "OpenMCM_FieldGuide"
PLUGIN = SCRIPT + ".esp"
FORM_ID = 0x02000800
PAGES = ["Overview", "Checklist", "Preferences"]
DATA_FILES = frozenset((
    "data/openmcm_fieldguide.esp", "data/seq/openmcm_fieldguide.seq",
    "data/scripts/openmcm_fieldguide.pex", "data/source/scripts/openmcm_fieldguide.psc",
))
SOURCE_PLUGIN_ROOT = "source/plugin/openmcm_fieldguide.esp/"
ROOT_REQUIRED = frozenset((
    "readme.md", "license", "docs/openmcm-api.md", "docs/building.md",
    SOURCE_PLUGIN_ROOT + "recorddata.yaml", SOURCE_PLUGIN_ROOT + "spriggit-meta.json",
    SOURCE_PLUGIN_ROOT + "quests/openmcm_fieldguidequest - 000800_openmcm_fieldguide.esp.yaml",
    "source/scripts/build-fieldguide.ps1", "source/tools/check_field_guide.py",
    "source/tools/check_mcm_contract.py", "source/tools/check_openmcm_api.py",
    "source/tools/repair_papyrus_identifiers.py",
    "source/tools/sanitize_papyrus_metadata.py",
))
PEX_CONTRACT = {
    "script": SCRIPT, "extends": "OpenMCM_ConfigBase",
    "required_identifiers": ["OnConfigInit", "OnPageReset", "GetPageToken", "IsPageTokenValid",
                             "SetCurrentPage", "SetOptionsEnabled", "SetOptionText", "SetLiveInfoText"],
    "required_exact_identifiers": [SCRIPT, "OpenMCM_ConfigBase"],
    "forbidden_identifiers": ["openMCM_FieldGuide", "openMCM_ConfigBase", "sKI_ConfigBase"],
}


class Reader:
    def __init__(self, data: bytes):
        self.data, self.offset = data, 0

    def take(self, length: int) -> bytes:
        if length < 0 or self.offset + length > len(self.data):
            raise ValueError(f"truncated structure at byte {self.offset}")
        value = self.data[self.offset:self.offset + length]
        self.offset += length
        return value

    def integer(self, fmt: str) -> int:
        return struct.unpack(fmt, self.take(struct.calcsize(fmt)))[0]

    def string(self) -> str:
        return self.take(self.integer("<H")).decode("utf-8")

    def done(self) -> None:
        if self.offset != len(self.data):
            raise ValueError("trailing structure bytes")


def subrecords(data: bytes) -> list[tuple[bytes, bytes]]:
    reader = Reader(data)
    fields = []
    while reader.offset < len(data):
        signature, length = reader.take(4), reader.integer("<H")
        # The tiny example has no reason to emit oversized fields.
        if signature == b"XXXX":
            raise ValueError("unexpected extended subrecord")
        fields.append((signature, reader.take(length)))
    return fields


def script(reader: Reader) -> tuple[str, dict[str, object]]:
    name = reader.string()
    reader.take(1)
    properties = {}
    for _ in range(reader.integer("<H")):
        key, kind = reader.string(), reader.integer("<B")
        reader.take(1)
        if key in properties:
            raise ValueError("duplicate VMAD property")
        if kind == 2:
            value = reader.string()
        elif kind == 12:
            value = [reader.string() for _ in range(reader.integer("<I"))]
        else:
            raise ValueError("unexpected VMAD property kind")
        properties[key] = value
    return name, properties


def validate_vmad(blob: bytes, report: Report) -> None:
    reader = Reader(blob)
    if tuple(reader.integer("<H") for _ in range(3)) != (5, 2, 1):
        raise ValueError("one version-5 quest script required")
    name, properties = script(reader)
    report.check(name == SCRIPT, "GUIDE_VMAD_SCRIPT: attach only OpenMCM_FieldGuide")
    report.check(properties == {"ModName": "OpenMCM Field Guide", "Pages": PAGES},
                 "GUIDE_VMAD_PROPERTIES: incorrect ModName or raw Pages")
    if (reader.integer("<B"), reader.integer("<H"), reader.string()) != (2, 0, ""):
        raise ValueError("quest fragments forbidden")
    if reader.integer("<H") != 1:
        raise ValueError("exactly one VMAD player reload alias required")
    reference = (reader.integer("<H"), reader.integer("<H"), reader.integer("<I"))
    report.check(reference == (0, 0, FORM_ID), "GUIDE_ALIAS_OWNER: alias must belong to own quest 02000800")
    if tuple(reader.integer("<H") for _ in range(3)) != (5, 2, 1):
        raise ValueError("exactly one version-5 alias script required")
    name, properties = script(reader)
    report.check(name == "SKI_PlayerLoadGameAlias" and not properties,
                 "GUIDE_ALIAS_SCRIPT: reuse host SKI_PlayerLoadGameAlias unchanged")
    reader.done()


def validate_plugin(blob: bytes, report: Report) -> None:
    try:
        records = list(_plugin_records(blob))
        if not report.check([r[0] for r in records] == [b"TES4", b"QUST"],
                            "GUIDE_RECORDS: only header and one new quest permitted"):
            return
        header, quest = records
        report.check(header[1] == 0 and header[2] == 0x200,
                     "GUIDE_PLUGIN_FLAGS: non-localized ESL-flagged ESP required")
        fields = subrecords(header[3])
        masters = [value for key, value in fields if key == b"MAST"]
        report.check(masters == [b"Skyrim.esm\0", b"SkyUI_SE.esp\0"],
                     "GUIDE_MASTERS: Skyrim.esm then SkyUI_SE.esp required")
        report.check(quest[1] == FORM_ID, "GUIDE_FORM: own master-index-2 local 000800 required")
        report.check(not quest[2] & 0x20, "GUIDE_DELETED: quest is deleted")
        fields = subrecords(quest[3])
        allowed = {b"EDID", b"VMAD", b"FULL", b"DNAM", b"NEXT", b"ANAM", b"ALST",
                   b"ALID", b"FNAM", b"ALFR", b"VTCK", b"ALED"}
        for name, _ in fields:
            report.check(name in allowed, f"GUIDE_SUBRECORD: forbidden {name!r}")
        report.check(len({key for key, _ in fields}) == len(fields), "GUIDE_DUPLICATE_SUBRECORD")
        data = dict(fields)
        report.check(data.get(b"EDID") == b"OpenMCM_FieldGuideQuest\0", "GUIDE_EDITOR_ID")
        dnam = data.get(b"DNAM", b"")
        report.check(len(dnam) == 12 and struct.unpack_from("<H", dnam)[0] & 0x111 == 0x111,
                     "GUIDE_QUEST_FLAGS: start-enabled run-once initialization required")
        for key, expected in ((b"ALST", struct.pack("<I", 0)), (b"ALID", b"PlayerAlias\0"),
                              (b"ALFR", struct.pack("<I", 0x14)), (b"ANAM", struct.pack("<I", 1)),
                              (b"FNAM", b"\0" * 4), (b"ALED", b"")):
            report.check(data.get(key) == expected, f"GUIDE_PLAYER_ALIAS: incorrect {key!r}")
        validate_vmad(data.get(b"VMAD", b""), report)
    except (ValueError, UnicodeDecodeError, struct.error, zlib.error) as error:
        report.check(False, f"GUIDE_PLUGIN_PARSE: {error}")


def validate_package(target: str | Path) -> Report:
    target = Path(target)
    report = Report(str(target.resolve()), "field-guide")
    try:
        # Unlike the host checker this sample always requires a Data wrapper.
        with PackageView(target) as view:
            keys = {entry.key for entry in view.entries}
            for path in sorted(DATA_FILES | ROOT_REQUIRED):
                report.check(path in keys, f"GUIDE_REQUIRED: missing {path}")
            for entry in view.entries:
                if entry.key.startswith("data/"):
                    report.check(entry.key in DATA_FILES, f"GUIDE_PAYLOAD: forbidden {entry.name}")
                else:
                    report.check(entry.key in ROOT_REQUIRED | {"openmcm_sha256sums.txt"}
                                 or entry.key.startswith("docs/") and entry.key.endswith(".md"),
                                 f"GUIDE_ROOT_PAYLOAD: forbidden {entry.name}")
            plugin = view.get("Data/" + PLUGIN)
            if plugin:
                validate_plugin(view.read_bytes(plugin), report)
            sequence = view.get("Data/Seq/OpenMCM_FieldGuide.seq")
            if sequence:
                report.check(view.read_bytes(sequence) == struct.pack("<I", FORM_ID), "GUIDE_SEQ")
            _validate_pex(view, report, PEX_CONTRACT)
            pex = view.get("Data/Scripts/OpenMCM_FieldGuide.pex")
            if pex:
                try:
                    data = view.read_bytes(pex)
                    strings, names = _parse_skyrim_pex_envelope(data)
                    report.check(names == [SCRIPT], "GUIDE_PEX_OBJECT")
                    report.check(_first_parent(data, strings) == "OpenMCM_ConfigBase", "GUIDE_PEX_PARENT")
                except (ValueError, UnicodeDecodeError, struct.error) as error:
                    report.check(False, f"GUIDE_PEX_PARSE: {error}")
            source = view.get("Data/Source/Scripts/OpenMCM_FieldGuide.psc")
            if source:
                text = "\n".join(_strip_papyrus_comment(line) for line in view.read_text(source).splitlines())
                report.check(re.search(r"(?im)^\s*Scriptname\s+OpenMCM_FieldGuide\s+extends\s+OpenMCM_ConfigBase\s*$", text)
                             is not None, "GUIDE_SOURCE_IDENTITY")
            _validate_checksum_manifest(view, report, required=True)
    except (OSError, ValueError) as error:
        report.check(False, f"GUIDE_PACKAGE: {error}")
    report.warn("Structural package checks do not replace in-game testing in each OpenMCM host mode.")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    args = parser.parse_args(argv)
    report = validate_package(args.target)
    for error in report.errors:
        print(f"ERROR: {error}")
    print(f"{'PASS' if report.ok else 'FAIL'}: {report.checks} Field Guide package checks")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
