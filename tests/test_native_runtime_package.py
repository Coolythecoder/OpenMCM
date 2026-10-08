from __future__ import annotations

import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from check_native_runtime import (  # noqa: E402
    DLL_PATH, INI_PATH, RUNTIME_VERSION, ValidationError,
    main, validate, validate_dll, validate_ini,
)


PE = 0x80
OPTIONAL = PE + 24
SECTION_TABLE = OPTIONAL + 0xF0
EXPORT_RAW = 0x600
METADATA_RAW = 0x800


def synthetic_dll() -> bytearray:
    """A minimal non-loadable fixture with real PE export indirection."""
    data = bytearray(0xC00)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, PE)
    data[PE:PE + 4] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, PE + 4, 0x8664, 2, 0, 0, 0, 0xF0, 0x2022)
    struct.pack_into("<H", data, OPTIONAL, 0x20B)
    struct.pack_into("<I", data, OPTIONAL + 108, 16)
    struct.pack_into("<II", data, OPTIONAL + 112, 0x2000, 0x100)
    for index, (name, virtual_size, rva, raw_size, raw, flags) in enumerate([
        (b".text", 0x100, 0x1000, 0x200, 0x400, 0x60000020),
        (b".rdata", 0x600, 0x2000, 0x600, 0x600, 0x40000040),
    ]):
        offset = SECTION_TABLE + index * 40
        data[offset:offset + len(name)] = name
        struct.pack_into("<IIII", data, offset + 8, virtual_size, rva, raw_size, raw)
        struct.pack_into("<I", data, offset + 36, flags)
    data[0x400:0x403] = b"\xB0\x01\xC3"
    struct.pack_into("<IIIIII", data, EXPORT_RAW + 16, 1, 2, 2, 0x2040, 0x2050, 0x2060)
    struct.pack_into("<II", data, EXPORT_RAW + 0x40, 0x1000, 0x2200)
    struct.pack_into("<II", data, EXPORT_RAW + 0x50, 0x2070, 0x2080)
    struct.pack_into("<HH", data, EXPORT_RAW + 0x60, 0, 1)
    data[0x670:0x680] = b"SKSEPlugin_Load\0\0"
    data[0x680:0x693] = b"SKSEPlugin_Version\0\0"
    struct.pack_into("<II", data, METADATA_RAW, 1, 1)
    data[METADATA_RAW + 8:METADATA_RAW + 23] = b"OpenMCMRuntime\0\0"
    struct.pack_into("<I", data, METADATA_RAW + 0x30C, RUNTIME_VERSION)
    return data


class NativeRuntimePEValidationTests(unittest.TestCase):
    def assert_bad(self, data: bytes, message: str) -> None:
        with self.assertRaisesRegex(ValidationError, message):
            validate_dll(data)

    def test_valid_real_export_tables_and_metadata(self):
        metadata = validate_dll(bytes(synthetic_dll()))
        self.assertEqual(metadata["runtime"], 0x01070680)
        self.assertEqual(metadata["plugin"], "OpenMCMRuntime")

    def test_rejects_wrong_machine(self):
        data = synthetic_dll()
        struct.pack_into("<H", data, PE + 4, 0x14C)
        self.assert_bad(data, "AMD64")

    def test_rejects_executable_instead_of_dll(self):
        data = synthetic_dll()
        struct.pack_into("<H", data, PE + 22, 0x22)
        self.assert_bad(data, "not a DLL")

    def test_strings_alone_do_not_count_as_exports(self):
        data = synthetic_dll()
        struct.pack_into("<I", data, EXPORT_RAW + 24, 1)
        self.assert_bad(data, "Missing actual PE export: SKSEPlugin_Version")

    def test_rejects_forwarded_export(self):
        data = synthetic_dll()
        struct.pack_into("<I", data, EXPORT_RAW + 0x40, 0x2070)
        self.assert_bad(data, "forwarded export")

    def test_rejects_noncode_load_export(self):
        data = synthetic_dll()
        struct.pack_into("<I", data, EXPORT_RAW + 0x40, 0x2200)
        self.assert_bad(data, "code export")

    def test_rejects_code_metadata_export(self):
        data = synthetic_dll()
        struct.pack_into("<I", data, SECTION_TABLE + 40 + 36, 0x60000040)
        self.assert_bad(data, "data export")

    def test_rejects_unbacked_export_address(self):
        data = synthetic_dll()
        struct.pack_into("<I", data, EXPORT_RAW + 0x44, 0x2500)
        self.assert_bad(data, "not backed")

    def test_rejects_invalid_export_ordinal(self):
        data = synthetic_dll()
        struct.pack_into("<H", data, EXPORT_RAW + 0x62, 2)
        self.assert_bad(data, "ordinal")

    def test_rejects_unbacked_export_name_table(self):
        data = synthetic_dll()
        struct.pack_into("<I", data, EXPORT_RAW + 32, 0xDEAD0000)
        self.assert_bad(data, "not backed")

    def test_rejects_old_runtime_and_additional_runtime(self):
        for offset, value in [(0x30C, 0x01064920), (0x310, 0x01064920)]:
            with self.subTest(offset=offset):
                data = synthetic_dll()
                struct.pack_into("<I", data, METADATA_RAW + offset, value)
                self.assert_bad(data, "Compatibility")

    def test_rejects_version_independence_claims(self):
        for offset in [0x304, 0x308]:
            with self.subTest(offset=offset):
                data = synthetic_dll()
                struct.pack_into("<I", data, METADATA_RAW + offset, 1)
                self.assert_bad(data, "version independence")

    def test_rejects_invalid_metadata_version_or_name(self):
        data = synthetic_dll()
        struct.pack_into("<I", data, METADATA_RAW, 2)
        self.assert_bad(data, "dataVersion")
        data = synthetic_dll()
        data[METADATA_RAW + 8] = ord("X")
        self.assert_bad(data, "plugin name")

    def test_rejects_nonterminated_and_nonascii_metadata(self):
        data = synthetic_dll()
        data[METADATA_RAW + 0x108:METADATA_RAW + 0x208] = b"A" * 256
        self.assert_bad(data, "null-terminated")
        data = synthetic_dll()
        data[METADATA_RAW + 0x208] = 0xFF
        self.assert_bad(data, "ASCII")

    def test_rejects_newer_required_skse(self):
        data = synthetic_dll()
        struct.pack_into("<I", data, METADATA_RAW + 0x34C, 0x03000000)
        self.assert_bad(data, "Minimum SKSE")

    def test_rejects_truncated_file_and_overlapping_sections(self):
        self.assert_bad(synthetic_dll()[:0xA00], "outside the file")
        data = synthetic_dll()
        struct.pack_into("<I", data, SECTION_TABLE + 40 + 12, 0x1100)
        self.assert_bad(data, "overlapping")


class NativeRuntimePackageTests(unittest.TestCase):
    INI = b"[Patches]\nDisableChargenPrecache=1\n"

    def test_valid_directory_and_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "release"
            dll = root / DLL_PATH
            dll.parent.mkdir(parents=True)
            dll.write_bytes(synthetic_dll())
            (root / INI_PATH).write_bytes(self.INI)
            self.assertEqual(validate(root)["plugin"], "OpenMCMRuntime")
            archive_path = Path(temp) / "release.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr(DLL_PATH.upper(), synthetic_dll())
                archive.writestr(INI_PATH, self.INI)
            self.assertEqual(validate(archive_path)["runtime"], RUNTIME_VERSION)
            self.assertEqual(main([str(archive_path)]), 0)

    def test_missing_dll_and_ini(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValidationError, "Missing runtime package file"):
                validate(root)
            dll = root / DLL_PATH
            dll.parent.mkdir(parents=True)
            dll.write_bytes(synthetic_dll())
            with self.assertRaisesRegex(ValidationError, "openmcmruntime.ini"):
                validate(root)

    def test_rejects_duplicate_zip_members(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "duplicate.zip"
            with zipfile.ZipFile(target, "w") as archive:
                archive.writestr(DLL_PATH, synthetic_dll())
                archive.writestr(DLL_PATH.upper(), synthetic_dll())
                archive.writestr(INI_PATH, self.INI)
            with self.assertRaisesRegex(ValidationError, "Duplicate runtime package file"):
                validate(target)

    def test_invalid_ini_default_or_format(self):
        for data in [b"[Patches]\nDisableChargenPrecache=0\n", b"[Patches]\n",
                     b"[Other]\nDisableChargenPrecache=1\n", b"not-an-ini"]:
            with self.subTest(data=data), self.assertRaises(ValidationError):
                validate_ini(data)


if __name__ == "__main__":
    unittest.main()
