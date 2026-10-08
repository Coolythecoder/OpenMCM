from __future__ import annotations

import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "tools", ROOT / "tests"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from check_skyui_coexist import (  # noqa: E402
    DEFAULT_CONTRACT, SCRIPTS, STATUS_FORM_ID, main, validate_package,
)
from test_contract_checker import (  # noqa: E402
    _minimal_pex, _minimal_swf, _record, _subrecord, _symbols_for, _write_checksum_manifest,
)
from test_native_runtime_package import synthetic_dll  # noqa: E402
from test_openmcm_api import api_fixture_payload  # noqa: E402


def _string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack("<H", len(encoded)) + encoded


def _status_vmad(*, script: str = "OpenMCM_ConfigMenu", owner: int = STATUS_FORM_ID,
                 alias_script: str = "SKI_PlayerLoadGameAlias", duplicate_script: bool = False) -> bytes:
    status = _string(script) + b"\0" + struct.pack("<H", 2)
    status += _string("ModName") + bytes((2, 1)) + _string("OpenMCM")
    status += _string("Pages") + bytes((12, 1)) + struct.pack("<I", 1) + _string("Status")
    vmad = struct.pack("<HHH", 5, 2, 2 if duplicate_script else 1) + status
    if duplicate_script:
        vmad += _string("SKI_ConfigManager") + b"\0\0\0"
    vmad += struct.pack("<BHHH", 2, 0, 0, 1)
    vmad += struct.pack("<HHIHHH", 0, 0, owner, 5, 2, 1)
    vmad += _string(alias_script) + b"\0\0\0"
    return vmad


def _status_plugin(*, form_id: int = STATUS_FORM_ID,
                   masters: tuple[str, ...] = ("Skyrim.esm", "SkyUI_SE.esp"),
                   vmad: bytes | None = None, extra_record: bytes = b"",
                   quest_suffix: bytes = b"", player_ref: int = 0x14,
                   plugin_flags: int = 0x200) -> bytes:
    header = _subrecord(b"HEDR", struct.pack("<fII", 1.7, 2, 0x801))
    for master in masters:
        header += _subrecord(b"MAST", master.encode() + b"\0") + _subrecord(b"DATA", b"\0" * 8)
    quest = _subrecord(b"EDID", b"OpenMCM_ConfigMenuInstance\0")
    quest += _subrecord(b"VMAD", _status_vmad() if vmad is None else vmad)
    quest += _subrecord(b"FULL", b"OpenMCM Config Menu\0")
    quest += _subrecord(b"DNAM", struct.pack("<H", 0x111) + b"\0" * 10)
    quest += _subrecord(b"NEXT", b"")
    quest += _subrecord(b"ANAM", struct.pack("<I", 1))
    quest += _subrecord(b"ALST", struct.pack("<I", 0))
    quest += _subrecord(b"ALID", b"PlayerAlias\0")
    quest += _subrecord(b"FNAM", b"\0" * 4)
    quest += _subrecord(b"ALFR", struct.pack("<I", player_ref))
    quest += _subrecord(b"VTCK", b"\0" * 4)
    quest += _subrecord(b"ALED", b"") + quest_suffix
    records = _record(b"QUST", form_id, quest) + extra_record
    group = b"GRUP" + struct.pack("<I", 24 + len(records)) + b"QUST" + b"\0" * 12 + records
    return _record(b"TES4", 0, header, flags=plugin_flags) + group


class SkyUICoexistValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(DEFAULT_CONTRACT.read_text(encoding="utf-8"))
        cls.contracts = {item["script"]: item for item in cls.contract["papyrus"]}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "Data"
        self.data.mkdir()
        self.write("OpenMCM.esp", _status_plugin())
        self.write("Seq/OpenMCM.seq", struct.pack("<I", STATUS_FORM_ID))
        for script in SCRIPTS:
            self.write_pex(script)
        for relative, raw in api_fixture_payload().items():
            self.write(relative, raw)
        tokens = []
        for asset in self.contract["ui_assets"]:
            tokens.extend(asset.get("required_release_tokens", asset.get("required_tokens", [])))
        self.tokens = list(dict.fromkeys(tokens))
        self.write("Interface/quest_journal.swf", _minimal_swf(self.tokens))

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative: str, content: bytes):
        path = self.data / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def write_pex(self, script: str, *, parent: str | None = None, remove: str | None = None):
        contract = self.contracts[script]
        symbols = _symbols_for(contract) | set(contract.get("required_literals", []))
        if remove is not None:
            symbols.discard(remove)
        self.write(f"Scripts/{script}.pex", _minimal_pex(symbols, script, parent or contract["extends"]))

    def assert_valid(self, target: Path | None = None):
        report = validate_package(target or self.root)
        self.assertTrue(report.ok, "\n".join(report.errors))
        self.assertEqual(report.profile, "skyui-coexist")
        self.assertTrue(any("in-game" in warning for warning in report.warnings))
        return report

    def assert_invalid(self, code: str, target: Path | None = None):
        report = validate_package(target or self.root)
        self.assertFalse(report.ok)
        self.assertTrue(any(code in error for error in report.errors), "\n".join(report.errors))

    def test_accepts_wrapped_and_flat_data_without_installed_skyui(self):
        self.assert_valid()
        self.assert_valid(self.data)

    def test_accepts_documented_package_root_and_three_matching_sources(self):
        (self.root / "README.md").write_text("Requires the real SkyUI plugin, not supplied here.")
        for script in SCRIPTS:
            self.write(f"Source/Scripts/{script}.psc", (ROOT / "src/papyrus" / f"{script}.psc").read_bytes())
        self.assert_valid()

    def test_forbids_standalone_and_non_mcm_assets(self):
        forbidden = [
            "SkyUI_SE.esp", "Seq/SkyUI_SE.seq", "Interface/Translations/SkyUI_SE_ENGLISH.txt",
            "Interface/Translations/OpenMCM_ENGLISH.txt", "Interface/inventorymenu.swf",
            "Interface/skyui/configpanel.swf", "SkyUI_SE.bsa", "Scripts/SKI_ConfigMenu.pex",
            "Scripts/SKI_QuestBase.pex", "Scripts/SKI_PlayerLoadGameAlias.pex",
            "Scripts/SKI_QF_ConfigManagerInstance.pex", "Source/Scripts/SKI_QuestBase.psc",
            "Scripts/MCM_ConfigBase.pex", "AnotherManager.esp", "nested/SkyUI_SE.esp",
        ]
        for name in forbidden:
            with self.subTest(name=name):
                self.write(name, b"must not ship")
                self.assert_invalid("COEXIST_PAYLOAD_FORBIDDEN")
                (self.data / name).unlink()

    def test_rejects_missing_required_payload(self):
        (self.data / "Seq/OpenMCM.seq").unlink()
        self.assert_invalid("COEXIST_PAYLOAD_MISSING")

    def test_requires_opt_in_api_pex_and_source_in_coexist_mode(self):
        for relative in api_fixture_payload():
            path = self.data / relative
            original = path.read_bytes()
            with self.subTest(relative=relative):
                path.unlink()
                self.assert_invalid("COEXIST_PAYLOAD_MISSING")
                path.write_bytes(original)

    def test_rejects_skyui_override_and_wrong_master_index(self):
        for form_id in (0x01000800, 0x01000802, 0x02000802, 0x00000800):
            with self.subTest(form_id=form_id):
                self.write("OpenMCM.esp", _status_plugin(form_id=form_id))
                self.assert_invalid("STATUS_FORM_MISMATCH")

    def test_rejects_wrong_or_extra_masters(self):
        for masters in (("Skyrim.esm",), ("SkyUI_SE.esp", "Skyrim.esm"),
                        ("Skyrim.esm", "SkyUI_SE.esp", "Other.esp")):
            with self.subTest(masters=masters):
                self.write("OpenMCM.esp", _status_plugin(masters=masters))
                self.assert_invalid("STATUS_MASTERS_MISMATCH")

    def test_rejects_non_light_or_esm_companion(self):
        for flags in (0, 0x201, 0x280):
            with self.subTest(flags=flags):
                self.write("OpenMCM.esp", _status_plugin(plugin_flags=flags))
                self.assert_invalid("STATUS_PLUGIN_FLAGS")

    def test_rejects_extra_quest_or_other_record_even_in_second_group(self):
        for record in (_record(b"QUST", 0x01000802, b""), _record(b"GLOB", 0x02000801, b"")):
            with self.subTest(record=record[:4]):
                self.write("OpenMCM.esp", _status_plugin(extra_record=record))
                self.assert_invalid("STATUS_RECORDS_MISMATCH")

    def test_rejects_second_script_or_manager_disguised_as_status(self):
        self.write("OpenMCM.esp", _status_plugin(vmad=_status_vmad(duplicate_script=True)))
        self.assert_invalid("STATUS_PLUGIN_PARSE_ERROR")
        self.write("OpenMCM.esp", _status_plugin(vmad=_status_vmad(script="SKI_ConfigManager")))
        self.assert_invalid("STATUS_SCRIPT_MISMATCH")

    def test_rejects_wrong_alias_owner_script_or_player(self):
        self.write("OpenMCM.esp", _status_plugin(vmad=_status_vmad(owner=0x01000830)))
        self.assert_invalid("STATUS_ALIAS_OWNER_MISMATCH")
        self.write("OpenMCM.esp", _status_plugin(vmad=_status_vmad(alias_script="SKI_ConfigManager")))
        self.assert_invalid("STATUS_ALIAS_SCRIPT_MISMATCH")
        self.write("OpenMCM.esp", _status_plugin(player_ref=0x15))
        self.assert_invalid("STATUS_PLAYER_REFERENCE_MISMATCH")

    def test_rejects_duplicate_vmad_and_trailing_plugin_subrecord_bytes(self):
        self.write("OpenMCM.esp", _status_plugin(quest_suffix=_subrecord(b"VMAD", _status_vmad())))
        self.assert_invalid("STATUS_SUBRECORD_DUPLICATE")
        self.write("OpenMCM.esp", _status_plugin(quest_suffix=b"bad"))
        self.assert_invalid("STATUS_PLUGIN_PARSE_ERROR")
        self.write("OpenMCM.esp", _status_plugin() + b"bad")
        self.assert_invalid("STATUS_PLUGIN_PARSE_ERROR")

    def test_rejects_malformed_vmad_not_just_missing_string_tokens(self):
        for vmad in (_status_vmad()[:-1], _status_vmad() + b"bad", b"OpenMCM_ConfigMenu SKI_PlayerLoadGameAlias"):
            with self.subTest(vmad=vmad[:15]):
                self.write("OpenMCM.esp", _status_plugin(vmad=vmad))
                self.assert_invalid("STATUS_PLUGIN_PARSE_ERROR")

    def test_seq_must_contain_only_self_status_quest(self):
        for sequence in (b"", struct.pack("<I", 0x01000800), struct.pack("<II", STATUS_FORM_ID, 0x01000802)):
            with self.subTest(sequence=sequence):
                self.write("Seq/OpenMCM.seq", sequence)
                self.assert_invalid("COEXIST_SEQ_MISMATCH")

    def test_compiled_pex_checks_symbols_real_parent_and_literals(self):
        self.write_pex("SKI_ConfigManager", remove="RegisterMod")
        self.assert_invalid("PEX_SYMBOL_MISSING")
        self.write_pex("SKI_ConfigManager", parent="Quest")
        self.assert_invalid("COEXIST_PEX_PARENT_MISMATCH")
        self.write_pex("SKI_ConfigManager", remove="SKICP_modSelected")
        self.assert_invalid("COEXIST_PEX_LITERAL_MISSING")

    def test_compiled_swf_bridge_and_structure_are_checked(self):
        self.write("Interface/quest_journal.swf", _minimal_swf([t for t in self.tokens if t != "setModNames"]))
        self.assert_invalid("SWF_TOKEN_MISSING")
        self.write("Interface/quest_journal.swf", b"FWS junk setModNames")
        self.assert_invalid("SWF_INVALID")

    def test_native_is_optional_paired_and_checked(self):
        self.write("SKSE/Plugins/OpenMCMRuntime.dll", bytes(synthetic_dll()))
        self.assert_invalid("COEXIST_NATIVE_PAIR_MISSING")
        self.write("SKSE/Plugins/OpenMCMRuntime.ini", (ROOT / "src/native/OpenMCMRuntime.ini").read_bytes())
        self.assert_valid()
        self.write("SKSE/Plugins/OpenMCMRuntime.dll", b"MZ broken")
        self.assert_invalid("COEXIST_NATIVE_INVALID")

    def test_mixed_flat_and_wrapped_payload_is_forbidden(self):
        (self.root / "OpenMCM.esp").write_bytes(_status_plugin())
        self.assert_invalid("MIXED_DATA_LAYOUT")
        self.assert_invalid("COEXIST_PAYLOAD_DUPLICATE")

    def make_zip(self, *, manifest: bool = True, extra: tuple[str, bytes] | None = None) -> Path:
        if manifest:
            _write_checksum_manifest(self.root)
        archive = self.root.parent / (self.root.name + ".zip")
        self.addCleanup(lambda: archive.unlink(missing_ok=True))
        with zipfile.ZipFile(archive, "w") as stream:
            for path in self.root.rglob("*"):
                if path.is_file():
                    stream.write(path, path.relative_to(self.root).as_posix())
            if extra:
                # ZipInfo's constructor normalizes backslashes on Windows;
                # preserve the malicious raw spelling for the security test.
                info = zipfile.ZipInfo("placeholder")
                info.filename = extra[0]
                info.orig_filename = extra[0]
                stream.writestr(info, extra[1])
        return archive

    def test_zip_accepts_only_exact_checksummed_payload(self):
        self.assert_valid(self.make_zip())

    def test_zip_rejects_missing_checksum_manifest(self):
        self.assert_invalid("CHECKSUM_MANIFEST_MISSING", self.make_zip(manifest=False))

    def test_zip_rejects_unlisted_extra_file_and_case_duplicate(self):
        self.assert_invalid("CHECKSUM_FILE_UNLISTED", self.make_zip(extra=("Data/readme.txt", b"unlisted")))
        self.assert_invalid("duplicate zip entry path", self.make_zip(extra=("data/OPENMCM.ESP", _status_plugin())))

    def test_zip_rejects_unsafe_paths(self):
        for name in ("../bad", "/absolute", "C:/absolute", "Data\\bad", "Data/../bad", "Data/bad:ads", "Data/bad."):
            with self.subTest(name=name):
                self.assert_invalid("unsafe" if ":ads" not in name and not name.endswith(".") else "UNSAFE_PACKAGE_PATH",
                                    self.make_zip(extra=(name, b"unsafe")))

    def test_rejects_symlink_directory_escape(self):
        link = self.data / "escape"
        try:
            link.symlink_to(self.root.parent, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("test host does not allow symlink creation")
        self.assert_invalid("unsafe directory entry")

    def test_cli_reports_json_and_missing_target_failure(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = main([str(self.root), "--json"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([str(self.root / "missing")]), 1)


if __name__ == "__main__":
    unittest.main()
