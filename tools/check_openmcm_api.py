#!/usr/bin/env python3
"""Validate the opt-in OpenMCM SDK files without altering the legacy SkyUI ABI.

This checks packaged source, coherent PEX identity/parents and capability symbols;
behavioral/source tests separately establish the implementation contract.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import struct
import sys

from check_mcm_contract import (PackageView, Report, _parse_skyrim_pex_envelope,
                                _strip_papyrus_comment, _validate_pex)


API_CONTRACTS = (
    {"script": "OpenMCM", "extends": "",
     "required_identifiers": ["GetAPIVersion", "GetHostAPIVersion", "HasCapability", "IsAPIEnabled"],
     "required_exact_identifiers": ["OpenMCM"],
     "forbidden_identifiers": ["openMCM"]},
    {"script": "OpenMCM_ConfigBase", "extends": "SKI_ConfigBase",
     "required_identifiers": [
         "BindOption", "BindStateOption", "GetOptionID", "GetPageToken", "IsPageTokenValid",
         "SetOptionLabel", "SetOptionText", "SetOptionHelp", "SetLiveInfoText",
         "SetCurrentPage", "SetOptionsEnabled",
         "AddNamedHeader", "AddNamedText", "AddNamedToggle", "AddNamedSlider",
         "AddNamedMenu", "AddNamedColor", "AddNamedKeyMap", "AddNamedInput",
     ],
     "required_exact_identifiers": ["OpenMCM_ConfigBase", "SKI_ConfigBase"],
     "forbidden_identifiers": ["openMCM_ConfigBase", "sKI_ConfigBase"]},
)
API_SCRIPTS = tuple(item["script"] for item in API_CONTRACTS)
API_PATHS = frozenset(path.casefold() for script in API_SCRIPTS
                      for path in (f"Scripts/{script}.pex", f"Source/Scripts/{script}.psc"))


def _first_parent(blob: bytes, strings: list[str]) -> str:
    """Read the parent only AFTER the existing envelope parser validates bounds."""
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
        raise ValueError("exactly one PEX object required")
    offset += 6
    index = u16()
    if index >= len(strings):
        raise ValueError("invalid PEX parent string index")
    return strings[index]


def validate_view(view: PackageView, report: Report) -> None:
    for contract in API_CONTRACTS:
        script = contract["script"]
        _validate_pex(view, report, contract)
        pex = view.get_data_path(f"Scripts/{script}.pex")
        if pex is not None:
            try:
                blob = view.read_bytes(pex)
                strings, objects = _parse_skyrim_pex_envelope(blob)
                report.check(objects == [script], f"OPENMCM_API_PEX_OBJECT: {script}")
                report.check(_first_parent(blob, strings) == contract["extends"],
                             f"OPENMCM_API_PEX_PARENT: {script}")
            except (ValueError, UnicodeDecodeError, struct.error) as error:
                report.check(False, f"OPENMCM_API_PEX_INVALID: {script}: {error}")
        source = view.get_data_path(f"Source/Scripts/{script}.psc")
        if not report.check(source is not None, f"OPENMCM_API_SOURCE_MISSING: {script}"):
            continue
        text = "\n".join(_strip_papyrus_comment(line) for line in view.read_text(source).splitlines())
        declaration = re.search(r"(?im)^\s*scriptname\s+(\w+)(?:\s+extends\s+(\w+))?", text)
        report.check(declaration is not None and declaration.group(1) == script
                     and (declaration.group(2) or "") == contract["extends"],
                     f"OPENMCM_API_SOURCE_IDENTITY: {script}")
        for function in contract["required_identifiers"]:
            report.check(re.search(rf"(?im)^\s*\w+\s+function\s+{re.escape(function)}\s*\(", text)
                         is not None, f"OPENMCM_API_SOURCE_FUNCTION: {script}.{function}")


def validate_package(target: str | Path) -> Report:
    target = Path(target)
    report = Report(str(target.resolve()), "openmcm-api")
    try:
        with PackageView(target) as view:
            validate_view(view, report)
    except (OSError, ValueError) as error:
        report.check(False, f"OPENMCM_API_PACKAGE_INVALID: {error}")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    args = parser.parse_args(argv)
    report = validate_package(args.target)
    for error in report.errors:
        print(f"ERROR: {error}")
    print(f"{'PASS' if report.ok else 'FAIL'}: {report.checks} opt-in API package checks")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
