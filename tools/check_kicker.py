#!/usr/bin/env python3
"""Validate the optional four-file Jaxonz MCM Kicker adapter (not a game test)."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import struct

from check_mcm_contract import (PackageView, Report, _parse_skyrim_pex_envelope,
                                _strip_papyrus_comment, _validate_pex)
from check_openmcm_api import _first_parent

RESET_METHOD = 'OpenMCM_TryForceReset'

CONTRACTS = (
    {"script": "JaxonzMCMKicker", "extends": "ReferenceAlias",
     "required_identifiers": ["OnInit", "OnPlayerLoadGame", "OnUpdate",
                              "OnConfigManagerReady", "OnMenuClose", RESET_METHOD,
                              "GetQuest", "IsMenuOpen", "UnregisterForUpdate",
                              "RegisterForModEvent", "RegisterForSingleUpdate",
                              "bMCMready", "iWaitSeconds", "iMCMregdelay", "iMaxWait"],
     "required_exact_identifiers": ["JaxonzMCMKicker", "ReferenceAlias",
                                    "SKI_ConfigManager", "SKI_ConfigManagerInstance", "Journal Menu", "RaceSex Menu"]},
    {"script": "JaxonzSKSEVersionCheckScript", "extends": "Quest",
     "required_identifiers": ["CheckSKSEVersion", "CheckSkyUIVersion", "GetVersionRelease",
                              "GetFormFromFile", "strModName", "sSKSEVersionRequired",
                              "iMinVersionRelease", "iWarnUser", "iSkyUIRequired",
                              "sUserWarningMessage"],
     "required_exact_identifiers": ["JaxonzSKSEVersionCheckScript", "Quest",
                                    "JaxonzMCMKicker.esp", "SKI_MainInstance",
                                    "SKI_ConfigManagerInstance"]},
)
DATA_FILES = frozenset(path.casefold() for item in CONTRACTS for path in
                      (f"Scripts/{item['script']}.pex", f"Source/Scripts/{item['script']}.psc"))


def validate_manager_bytes(pex: bytes, source: bytes) -> Report:
    """Reject mixing the adapter with a host that lacks its completion method.

    This structural gate checks packaged bytes/source, not VM behaviour.
    """
    report = Report('Kicker host manager', 'kicker-host')
    try:
        strings, objects = _parse_skyrim_pex_envelope(pex)
        report.check(objects == ['SKI_ConfigManager'], 'KICKER_HOST_OBJECT: SKI_ConfigManager required')
        report.check(_first_parent(pex, strings) == 'SKI_QuestBase', 'KICKER_HOST_PARENT: SKI_QuestBase required')
        report.check(RESET_METHOD.casefold() in {s.casefold() for s in strings},
                     'KICKER_HOST_ACK: compiled manager lacks completion method')
        text = '\n'.join(_strip_papyrus_comment(line) for line in source.decode('utf-8-sig').splitlines())
        bodies = re.findall(rf'(?ims)^\s*Bool\s+Function\s+{RESET_METHOD}\(\)\s*\n(.*?)^\s*EndFunction\b', text)
        report.check(len(bodies) == 2, 'KICKER_HOST_ACK: default and BUSY Boolean implementations required')
        if len(bodies) == 2:
            report.check('Return True' in bodies[0] and bodies[1].strip().casefold() == 'return false',
                         'KICKER_HOST_ACK: completion and BUSY rejection results required')
    except (ValueError, UnicodeDecodeError, struct.error) as error:
        report.check(False, f'KICKER_HOST_ACK: invalid manager: {error}')
    return report


def validate_package(target: str | Path) -> Report:
    target = Path(target)
    report = Report(str(target.resolve()), "jaxonz-kicker")
    try:
        with PackageView(target) as view:
            keys = {e.key[5:] if e.key.startswith('data/') else e.key for e in view.entries}
            report.check(keys == DATA_FILES and len(view.entries) == 4,
                         'KICKER_PAYLOAD: exactly two compiled scripts and their two sources required')
            for contract in CONTRACTS:
                script = contract['script']
                _validate_pex(view, report, contract)
                entry = view.get_data_path(f'Scripts/{script}.pex')
                if entry:
                    try:
                        raw = view.read_bytes(entry)
                        report.check(len(raw) <= 1024 * 1024, f'KICKER_PEX_SIZE: {script}')
                        strings, objects = _parse_skyrim_pex_envelope(raw)
                        report.check(objects == [script], f'KICKER_PEX_OBJECT: {script}')
                        report.check(_first_parent(raw, strings) == contract['extends'],
                                     f'KICKER_PEX_PARENT: {script}')
                        if script == 'JaxonzMCMKicker':
                            report.check('setstage' not in {s.casefold() for s in strings},
                                         'KICKER_ACK: stage requests cannot acknowledge reset completion')
                    except (ValueError, UnicodeDecodeError, struct.error) as error:
                        report.check(False, f'KICKER_PEX_INVALID: {script}: {error}')
                source = view.get_data_path(f'Source/Scripts/{script}.psc')
                if not report.check(source is not None, f'KICKER_SOURCE_MISSING: {script}'):
                    continue
                raw_source = view.read_text(source)
                report.check(len(raw_source) <= 128 * 1024, f'KICKER_SOURCE_SIZE: {script}')
                text = '\n'.join(_strip_papyrus_comment(line) for line in raw_source.splitlines())
                report.check(re.search(rf'(?im)^\s*Scriptname\s+{script}\s+extends\s+{contract["extends"]}\s*$', text)
                             is not None, f'KICKER_SOURCE_IDENTITY: {script}')
                for token in contract['required_identifiers']:
                    report.check(re.search(rf'(?i)\b{re.escape(token)}\b', text) is not None,
                                 f'KICKER_SOURCE_CONTRACT: {script}.{token}')
                report.check('36801' in raw_source and 'Jaxonz' in raw_source and 'insaneplumber' in raw_source,
                             f'KICKER_CREDITS: {script}')
    except (OSError, ValueError) as error:
        report.check(False, f'KICKER_PACKAGE: {error}')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    report = validate_package(parser.parse_args().target)
    for error in report.errors:
        print(f'ERROR: {error}')
    print(f'{"PASS" if report.ok else "FAIL"}: {report.checks} Kicker adapter package checks')
    return 0 if report.ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
