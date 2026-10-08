"""Adversarial inventories and PEX/source contracts for the BASIC Bridge addon.

Tiny coherent PEX envelopes test structural packaging, not Papyrus execution.
The companion SDK tests inspect actual adapter source behavior separately.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_mcm_bridge_addon as checker


def pex(script: str, parent: str, symbols=()) -> bytes:
    values = sorted({script, parent, "", *symbols})
    indices = {value: index for index, value in enumerate(values)}

    def string(text):
        raw = text.encode("utf-8")
        return struct.pack(">H", len(raw)) + raw

    header = bytes.fromhex("fa57c0de") + bytes((3, 2)) + struct.pack(">HQ", 1, 0)
    header += string(f"{script}.psc") + string("OpenMCM") + string("Build")
    table = struct.pack(">H", len(values)) + b"".join(string(value) for value in values)
    metadata = b"\0" + struct.pack(">HH", 0, 1)
    block = struct.pack(">HHIHHHH", indices[parent], indices[""], 0, indices[""], 0, 0, 0)
    return header + table + metadata + struct.pack(">H", indices[script]) + struct.pack("<I", len(block)) + block


def zipped(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in files.items():
            info = zipfile.ZipInfo()
            info.filename = name  # Preserve malicious Windows separators for safety tests.
            archive.writestr(info, raw)
    return output.getvalue()


def manifest(files):
    files["SHA256SUMS.txt"] = "".join(
        f"{hashlib.sha256(raw).hexdigest().upper()}  {name}\n"
        for name, raw in sorted(files.items()) if name != "SHA256SUMS.txt"
    ).encode()


class BridgeAddonPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / "addon.zip"
        self.version = "0.1.0"
        self.source_name = f"source/OpenMCM-MCM-Bridge-Addon-{self.version}-Source.zip"
        self.files = {name: b"BASIC addon notice\n" for name in checker.ROOT_FILES}
        self.files["LICENSE.txt"] = (ROOT / "LICENSE.txt").read_bytes()
        self.source = {name: b"# Editable source fixture\n" for name in checker.SOURCE_FILES}
        self.source["LICENSE.txt"] = self.files["LICENSE.txt"]
        self.source["vendor/papyrus-stubs/Quest.psc"] = b"Scriptname Quest extends Form\n"
        for script, (parent, methods) in checker.SCRIPTS.items():
            self.files[f"Data/Scripts/{script}.pex"] = pex(script, parent, methods)
            text = f"Scriptname {script}" + (f" extends {parent}" if parent else " Hidden") + "\n"
            for method in methods:
                text += f"Int Function {method}()\n    Return 0\nEndFunction\n"
            raw = text.encode()
            self.files[f"Data/Source/Scripts/{script}.psc"] = raw
            self.source[f"src/compat/mcm-bridge/{script}.psc"] = raw
        for name in ("README.md", "THIRD_PARTY_NOTICES.md"):
            self.source[f"src/compat/mcm-bridge/{name}"] = self.files[name]
        self.pin = {"repository": "https://example.invalid/mcm-bridge", "version": checker.BRIDGE_VERSION,
                    "commit": checker.BRIDGE_COMMIT, "files": {
                        name: hashlib.sha256(self.source[f"upstream/mcm-bridge/{name}"]).hexdigest().upper()
                        for name in checker.UPSTREAM_FILES}}
        self.source["src/compat/mcm-bridge/upstream.json"] = json.dumps(self.pin).encode()
        self.metadata = {"project": checker.PROJECT, "version": self.version, "openMCMApiVersion": 1,
                         "host": "MCM Bridge", "bridgeVersion": checker.BRIDGE_VERSION,
                         "bridgeCommit": checker.BRIDGE_COMMIT, "capabilities": ["named_options"],
                         "apiEnabled": False, "inGameVerified": False, "sourceArchive": self.source_name}

    def write(self, *, source_manifest=True, package_manifest=True):
        if source_manifest:
            manifest(self.source)
        raw = zipped(self.source)
        self.files[self.source_name] = raw
        self.metadata["sourceSha256"] = hashlib.sha256(raw).hexdigest().upper()
        self.files["OpenMCM_BRIDGE_ADDON.json"] = json.dumps(self.metadata).encode()
        if package_manifest:
            manifest(self.files)
        self.archive.write_bytes(zipped(self.files))

    def validate(self):
        return checker.validate_package(self.archive)

    def invalid(self, fragment):
        report = self.validate()
        self.assertFalse(report.ok)
        self.assertTrue(any(fragment in error for error in report.errors), report.errors)

    def test_accepts_minimal_separate_zip_and_directory(self):
        self.write()
        report = self.validate()
        self.assertTrue(report.ok, report.errors)
        directory = Path(self.temp.name) / "unpacked"
        for name, raw in self.files.items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        report = checker.validate_package(directory)
        self.assertTrue(report.ok, report.errors)

    def test_rejects_any_extra_runtime_payload(self):
        for name in ("Data/Scripts/SKI_ConfigBase.pex", "Data/Scripts/MCMBridgeNative.pex",
                     "Data/Interface/quest_journal.swf", "Data/SKSE/Plugins/OpenMCMRuntime.dll",
                     "Data/OpenMCM.esp", "Data/Scripts/unexpected.pex", "fomod/ModuleConfig.xml"):
            with self.subTest(name=name):
                self.files[name] = b"Forbidden runtime fixture"
                self.write()
                self.invalid("PACKAGE_UNEXPECTED")
                del self.files[name]

    def test_rejects_missing_runtime_or_source_member(self):
        for name in checker.RUNTIME_FILES:
            with self.subTest(name=name):
                original = self.files.pop(name)
                self.write()
                self.invalid("PACKAGE_MISSING")
                self.files[name] = original

    def test_requires_corresponding_source_components(self):
        for name in ("scripts/Build-MCMBridgeAddon.ps1", "tools/sanitize_papyrus_metadata.py",
                     "tests/test_bridge_sdk.py", "src/papyrus/OpenMCM.psc",
                     "upstream/mcm-bridge/LICENSE"):
            with self.subTest(name=name):
                original = self.source.pop(name)
                self.write()
                self.invalid("SOURCE_MISSING")
                self.source[name] = original

    def test_rejects_unlisted_and_bad_checksums(self):
        self.write()
        self.files["README.md"] += b"Unrecorded mutation\n"
        self.archive.write_bytes(zipped(self.files))
        self.invalid("PACKAGE_CHECKSUM")
        self.write()
        self.files["SHA256SUMS.txt"] += b"0" * 64 + b"  imaginary.txt\n"
        self.archive.write_bytes(zipped(self.files))
        self.invalid("PACKAGE_MANIFEST_INVENTORY")

    def test_rejects_source_checksum_mismatch(self):
        self.write()
        self.source["scripts/Build-MCMBridgeAddon.ps1"] += b"Changed source\n"
        self.write(source_manifest=False)
        self.invalid("SOURCE_CHECKSUM")

    def test_rejects_source_archive_wrong_hash(self):
        self.write()
        self.metadata["sourceSha256"] = "0" * 64
        self.files["OpenMCM_BRIDGE_ADDON.json"] = json.dumps(self.metadata).encode()
        manifest(self.files)
        self.archive.write_bytes(zipped(self.files))
        self.invalid("SOURCE_ARCHIVE_HASH")

    def test_rejects_unsafe_outer_paths_and_case_duplicates(self):
        for name in ("../outside.txt", "/absolute.txt", "C:/outside.txt", "Data\\escaped.txt",
                     "Data/NUL.txt", "Data/trailing./bad.txt", "Data/file.txt:stream", "readme.md"):
            with self.subTest(name=name):
                self.write()
                bad = dict(self.files, **{name: b"Bad entry\n"})
                self.archive.write_bytes(zipped(bad))
                self.invalid("PACKAGE_INVALID")

    def test_rejects_unsafe_source_paths(self):
        self.source["../outside.txt"] = b"bad"
        self.write()
        self.invalid("Unsafe archive path")

    def test_rejects_embedded_runtime_and_private_artifacts(self):
        for name in ("upstream/mcm-bridge/scripts/Compiled/SKI_ConfigBase.pex", "build/player.dmp",
                     "dist/old.zip", ".git/config", "tools/private.dll"):
            with self.subTest(name=name):
                self.source[name] = b"Forbidden fixture"
                self.write()
                self.invalid("SOURCE_UNEXPECTED")
                del self.source[name]

    def test_rejects_nontext_disguised_as_source(self):
        self.source["scripts/Build-MCMBridgeAddon.ps1"] = b"MZ\0\0executable"
        self.write()
        self.invalid("SOURCE_NOT_TEXT")

    def test_rejects_pex_bad_parent_or_case(self):
        name = "Data/Scripts/OpenMCM_ConfigBase.pex"
        for parent in ("Quest", "sKI_ConfigBase"):
            with self.subTest(parent=parent):
                self.files[name] = pex("OpenMCM_ConfigBase", parent, checker.BASE_FUNCTIONS)
                self.write()
                self.invalid("PEX_PARENT")

    def test_rejects_pex_envelope_damage_and_trailing_data(self):
        name = "Data/Scripts/OpenMCM.pex"
        original = self.files[name]
        for raw in (original[:-1], original + b"trailing", b"not PEX", b"\0" + original[1:]):
            with self.subTest(length=len(raw)):
                self.files[name] = raw
                self.write()
                self.invalid("PEX_INVALID")

    def test_rejects_missing_named_api_symbols(self):
        self.files["Data/Scripts/OpenMCM_ConfigBase.pex"] = pex("OpenMCM_ConfigBase", "SKI_ConfigBase")
        self.write()
        self.invalid("PEX_SYMBOL")

    def test_rejects_original_host_dependencies_in_pex_and_psc(self):
        name = "Data/Scripts/OpenMCM.pex"
        original = self.files[name]
        for symbol in ("UI", "SKI_ConfigManager", "IsOpenMCMAPIEnabled", "_root.ConfigPanelFader.configPanel"):
            with self.subTest(symbol=symbol):
                self.files[name] = pex("OpenMCM", "", (*checker.SCRIPTS["OpenMCM"][1], symbol))
                self.write()
                self.invalid("PEX_HOST_DEPENDENCY")
        self.files[name] = original
        self.files["Data/Source/Scripts/OpenMCM.psc"] += b"UI.GetInt(\"Journal Menu\", \"_root.example\")\n"
        self.write()
        self.invalid("PSC_HOST_DEPENDENCY")

    def test_requires_source_runtime_byte_parity(self):
        self.source["src/compat/mcm-bridge/OpenMCM.psc"] += b"; Not the installed source\n"
        self.write()
        self.invalid("SOURCE_RUNTIME_MISMATCH")

    def test_rejects_claimed_extended_capabilities_and_tested_status(self):
        for key, value in (("capabilities", ["named_options", "page_tokens"]),
                           ("apiEnabled", True), ("inGameVerified", True),
                           ("bridgeVersion", "99.0.0"), ("openMCMApiVersion", True)):
            with self.subTest(key=key):
                original = self.metadata[key]
                self.metadata[key] = value
                self.write()
                self.invalid("METADATA_VALUE")
                self.metadata[key] = original

    def test_requires_exact_source_archive_version(self):
        self.metadata["sourceArchive"] = "source/wrong-version.zip"
        self.write()
        self.invalid("METADATA_SOURCE_PATH")

    def test_rejects_source_pin_changes_and_upstream_mutation(self):
        self.pin["commit"] = "f" * 40
        self.source["src/compat/mcm-bridge/upstream.json"] = json.dumps(self.pin).encode()
        self.write()
        self.invalid("SOURCE_UPSTREAM_IDENTITY")
        self.pin["commit"] = checker.BRIDGE_COMMIT
        self.source["src/compat/mcm-bridge/upstream.json"] = json.dumps(self.pin).encode()
        self.source["upstream/mcm-bridge/scripts/Source/host/SKI_ConfigBase.psc"] += b"Mutation\n"
        self.write()
        self.invalid("SOURCE_UPSTREAM_HASH")

    def test_requires_full_unchanged_gpl_in_both_locations(self):
        self.files["LICENSE.txt"] += b"Additional restriction\n"
        self.write()
        self.invalid("PACKAGE_GPL_FULL_TEXT")
        self.files["LICENSE.txt"] = (ROOT / "LICENSE.txt").read_bytes()
        self.source["LICENSE.txt"] = b"GNU GENERAL PUBLIC LICENSE Version 3\n"
        self.write()
        self.invalid("SOURCE_GPL_FULL_TEXT")

    def test_accepts_gpl_only_line_ending_conversion(self):
        raw = (ROOT / "LICENSE.txt").read_bytes().replace(b"\r\n", b"\n")
        self.files["LICENSE.txt"] = raw.replace(b"\n", b"\r\n")
        self.source["LICENSE.txt"] = raw
        self.write()
        report = self.validate()
        self.assertTrue(report.ok, report.errors)


if __name__ == "__main__":
    unittest.main()
