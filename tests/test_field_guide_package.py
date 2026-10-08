from __future__ import annotations

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

from check_field_guide import (  # noqa: E402
    DATA_FILES, FORM_ID, PAGES, PEX_CONTRACT, ROOT_REQUIRED, SCRIPT, validate_package,
)
from check_mcm_contract import _parse_skyrim_pex_envelope  # noqa: E402
from repair_papyrus_identifiers import repair_bytes  # noqa: E402
from test_contract_checker import _minimal_pex, _record, _subrecord, _write_checksum_manifest  # noqa: E402


def string(value: str) -> bytes:
    raw = value.encode()
    return struct.pack("<H", len(raw)) + raw


def vmad(*, name=SCRIPT, owner=FORM_ID, pages=None, alias="SKI_PlayerLoadGameAlias") -> bytes:
    page_names = PAGES if pages is None else pages
    result = struct.pack("<HHH", 5, 2, 1) + string(name) + b"\0" + struct.pack("<H", 2)
    result += string("ModName") + bytes((2, 1)) + string("OpenMCM Field Guide")
    result += string("Pages") + bytes((12, 1)) + struct.pack("<I", len(page_names))
    result += b"".join(string(page) for page in page_names)
    result += struct.pack("<BHHH", 2, 0, 0, 1)
    result += struct.pack("<HHIHHH", 0, 0, owner, 5, 2, 1)
    return result + string(alias) + b"\0\0\0"


def plugin(*, form=FORM_ID, masters=("Skyrim.esm", "SkyUI_SE.esp"), script_data=None,
           extra=b"", suffix=b"", player=0x14, flags=0x200, quest_flags=0x111) -> bytes:
    header = _subrecord(b"HEDR", struct.pack("<fII", 1.7, 1, 0x801))
    for master in masters:
        header += _subrecord(b"MAST", master.encode() + b"\0") + _subrecord(b"DATA", b"\0" * 8)
    quest = _subrecord(b"EDID", b"OpenMCM_FieldGuideQuest\0")
    quest += _subrecord(b"VMAD", vmad() if script_data is None else script_data)
    quest += _subrecord(b"FULL", b"OpenMCM Field Guide\0")
    quest += _subrecord(b"DNAM", struct.pack("<H", quest_flags) + b"\0" * 10)
    quest += _subrecord(b"NEXT", b"") + _subrecord(b"ANAM", struct.pack("<I", 1))
    quest += _subrecord(b"ALST", b"\0" * 4) + _subrecord(b"ALID", b"PlayerAlias\0")
    quest += _subrecord(b"FNAM", b"\0" * 4) + _subrecord(b"ALFR", struct.pack("<I", player))
    quest += _subrecord(b"VTCK", b"\0" * 4) + _subrecord(b"ALED", b"") + suffix
    records = _record(b"QUST", form, quest) + extra
    group = b"GRUP" + struct.pack("<I", 24 + len(records)) + b"QUST" + b"\0" * 12 + records
    return _record(b"TES4", 0, header, flags=flags) + group


class FieldGuidePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        for name in ROOT_REQUIRED:
            self.write(name, b"documentation / source fixture")
        self.write("Data/OpenMCM_FieldGuide.esp", plugin())
        self.write("Data/Seq/OpenMCM_FieldGuide.seq", struct.pack("<I", FORM_ID))
        self.write_pex()
        self.write("Data/Source/Scripts/OpenMCM_FieldGuide.psc",
                   b"Scriptname OpenMCM_FieldGuide extends OpenMCM_ConfigBase\n")

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def write_pex(self, *, name=SCRIPT, parent="OpenMCM_ConfigBase", remove=None):
        symbols = set(PEX_CONTRACT["required_identifiers"]) | {SCRIPT, "OpenMCM_ConfigBase"}
        if remove:
            symbols.remove(remove)
        self.write("Data/Scripts/OpenMCM_FieldGuide.pex", _minimal_pex(symbols, name, parent))

    def report(self, *, rewrite_checksums=True):
        if rewrite_checksums:
            _write_checksum_manifest(self.root)
        return validate_package(self.root)

    def valid(self):
        result = self.report()
        self.assertTrue(result.ok, "\n".join(result.errors))

    def invalid(self, code):
        result = self.report()
        self.assertFalse(result.ok)
        self.assertTrue(any(code in error for error in result.errors), "\n".join(result.errors))

    def test_minimal_package(self):
        self.valid()

    def test_checksums_and_zip(self):
        self.valid()
        archive = self.root.parent / (self.root.name + ".zip")
        self.addCleanup(lambda: archive.unlink(missing_ok=True))
        with zipfile.ZipFile(archive, "w") as output:
            for path in self.root.rglob("*"):
                if path.is_file():
                    output.write(path, path.relative_to(self.root).as_posix())
        result = validate_package(archive)
        self.assertTrue(result.ok, result.errors)

    def test_each_required_file(self):
        for relative in DATA_FILES | ROOT_REQUIRED:
            with self.subTest(relative=relative):
                path = next(path for path in self.root.rglob("*")
                            if path.is_file() and path.relative_to(self.root).as_posix().casefold() == relative)
                original = path.read_bytes()
                path.unlink()
                self.invalid("GUIDE_REQUIRED")
                path.write_bytes(original)

    def test_no_host_overrides_or_engine_stubs(self):
        for name in ("SkyUI_SE.esp", "Scripts/SKI_ConfigBase.pex", "Scripts/OpenMCM_ConfigBase.pex",
                     "Scripts/SKI_PlayerLoadGameAlias.pex", "Source/Scripts/Actor.psc",
                     "Interface/quest_journal.swf", "SKSE/Plugins/Example.dll", "another.esp"):
            with self.subTest(name=name):
                self.write("Data/" + name, b"unexpected")
                self.invalid("GUIDE_PAYLOAD")
                (self.root / "Data" / name).unlink()

    def test_no_runtime_binary_disguised_as_source(self):
        self.write("Source/Example.dll", b"MZ")
        self.invalid("GUIDE_ROOT_PAYLOAD")

    def test_no_flat_data_layout(self):
        self.write("OpenMCM_FieldGuide.esp", plugin())
        self.invalid("GUIDE_ROOT_PAYLOAD")

    def test_own_form_not_skyui_override(self):
        for form in (0x01000800, 0x01000802, 0x02000801, 0x800):
            with self.subTest(form=form):
                self.write("Data/OpenMCM_FieldGuide.esp", plugin(form=form))
                self.invalid("GUIDE_FORM")

    def test_master_order_and_no_extra_master(self):
        for masters in (("Skyrim.esm",), ("SkyUI_SE.esp", "Skyrim.esm"),
                        ("Skyrim.esm", "SkyUI_SE.esp", "Other.esp")):
            with self.subTest(masters=masters):
                self.write("Data/OpenMCM_FieldGuide.esp", plugin(masters=masters))
                self.invalid("GUIDE_MASTERS")

    def test_only_own_quest_record(self):
        self.write("Data/OpenMCM_FieldGuide.esp", plugin(extra=_record(b"GLOB", 0x02000801, b"")))
        self.invalid("GUIDE_RECORDS")

    def test_esl_start_enabled_flags(self):
        for flags in (0, 0x201, 0x280):
            self.write("Data/OpenMCM_FieldGuide.esp", plugin(flags=flags))
            self.invalid("GUIDE_PLUGIN_FLAGS")
        self.write("Data/OpenMCM_FieldGuide.esp", plugin(quest_flags=0x110))
        self.invalid("GUIDE_QUEST_FLAGS")

    def test_vmad_script_and_pages(self):
        self.write("Data/OpenMCM_FieldGuide.esp", plugin(script_data=vmad(name="SKI_ConfigManager")))
        self.invalid("GUIDE_VMAD_SCRIPT")
        self.write("Data/OpenMCM_FieldGuide.esp", plugin(script_data=vmad(pages=["Wrong"])))
        self.invalid("GUIDE_VMAD_PROPERTIES")

    def test_player_reload_alias_owner_and_script(self):
        self.write("Data/OpenMCM_FieldGuide.esp", plugin(script_data=vmad(owner=0x01000802)))
        self.invalid("GUIDE_ALIAS_OWNER")
        self.write("Data/OpenMCM_FieldGuide.esp", plugin(script_data=vmad(alias="OpenMCM_FieldGuide")))
        self.invalid("GUIDE_ALIAS_SCRIPT")
        self.write("Data/OpenMCM_FieldGuide.esp", plugin(player=0x15))
        self.invalid("GUIDE_PLAYER_ALIAS")

    def test_malformed_vmad_and_duplicate_fields(self):
        for data in (vmad()[:-1], vmad() + b"bad", b"OpenMCM_FieldGuide"):
            self.write("Data/OpenMCM_FieldGuide.esp", plugin(script_data=data))
            self.invalid("GUIDE_PLUGIN_PARSE")
        self.write("Data/OpenMCM_FieldGuide.esp", plugin(suffix=_subrecord(b"VMAD", vmad())))
        self.invalid("GUIDE_DUPLICATE_SUBRECORD")

    def test_seq_exact_own_form(self):
        for value in (b"", struct.pack("<I", 0x01000800), struct.pack("<II", FORM_ID, FORM_ID)):
            self.write("Data/Seq/OpenMCM_FieldGuide.seq", value)
            self.invalid("GUIDE_SEQ")

    def test_pex_real_identity_parent_and_symbol(self):
        self.write_pex(name="Different")
        self.invalid("GUIDE_PEX_OBJECT")
        self.write_pex(parent="SKI_ConfigBase")
        self.invalid("GUIDE_PEX_PARENT")
        self.write_pex(remove="SetCurrentPage")
        self.invalid("PEX_SYMBOL_MISSING")

    def test_pex_and_source_case(self):
        self.write_pex(parent="openMCM_ConfigBase")
        self.invalid("PEX_FORBIDDEN_IDENTIFIER")
        self.write_pex()
        self.write("Data/Source/Scripts/OpenMCM_FieldGuide.psc",
                   b"Scriptname Another extends OpenMCM_ConfigBase\n")
        self.invalid("GUIDE_SOURCE_IDENTITY")

    def test_corrupt_pex(self):
        self.write("Data/Scripts/OpenMCM_FieldGuide.pex", b"\xfa\x57\xc0\xdeOpenMCM_FieldGuide")
        self.invalid("PEX_PARSE_ERROR")

    def test_checksum_missing_and_tampering(self):
        result = self.report(rewrite_checksums=False)
        self.assertIn("CHECKSUM_MANIFEST_MISSING", "\n".join(result.errors))
        self.valid()
        self.write("README.md", b"changed after checksumming")
        result = self.report(rewrite_checksums=False)
        self.assertIn("CHECKSUM_MISMATCH", "\n".join(result.errors))


class IdentifierRepairTests(unittest.TestCase):
    def test_repairs_complete_table_entries_without_changing_length(self):
        data = _minimal_pex({"sKI_ConfigBase[]", "stringUtil", "prefix openMCM_ConfigBase suffix"},
                            SCRIPT, "openMCM_ConfigBase")
        repaired, count = repair_bytes(data)
        self.assertEqual(count, 3)
        self.assertEqual(len(data), len(repaired))
        strings, _ = _parse_skyrim_pex_envelope(repaired)
        self.assertIn("OpenMCM_ConfigBase", strings)
        self.assertIn("SKI_ConfigBase[]", strings)
        self.assertIn("StringUtil", strings)
        self.assertIn("prefix openMCM_ConfigBase suffix", strings)

    def test_canonical_input_is_unchanged(self):
        data = _minimal_pex(set(), SCRIPT, "OpenMCM_ConfigBase")
        self.assertEqual(repair_bytes(data), (data, 0))

    def test_malformed_input_rejected(self):
        with self.assertRaises(ValueError):
            repair_bytes(b"not a PEX")


if __name__ == "__main__":
    unittest.main()
