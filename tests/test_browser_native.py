"""Native browser artifact contracts; fixtures are not executable game tests."""
from __future__ import annotations
import struct
import hashlib
import io
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_browser_native import RUNTIMES, validate_dll
from check_native_runtime import ValidationError
from test_native_runtime_package import synthetic_dll, EXPORT_RAW, METADATA_RAW
from package_browser_native_source import dependency_source


def browser_fixture() -> bytearray:
    data = synthetic_dll()
    struct.pack_into("<IIIIII", data, EXPORT_RAW + 16, 1, 3, 3, 0x2040, 0x2050, 0x2060)
    struct.pack_into("<III", data, EXPORT_RAW + 0x40, 0x1000, 0x2200, 0x1000)
    struct.pack_into("<III", data, EXPORT_RAW + 0x50, 0x2070, 0x2080, 0x20A0)
    struct.pack_into("<HHH", data, EXPORT_RAW + 0x60, 0, 1, 2)
    data[0x6A0:0x6B1] = b"SKSEPlugin_Query\0"
    data[METADATA_RAW + 8:METADATA_RAW + 0x108] = b"OpenMCMBrowser\0".ljust(256, b"\0")
    data[METADATA_RAW + 0x108:METADATA_RAW + 0x208] = b"OpenMCM / SpawneR27\0".ljust(256, b"\0")
    struct.pack_into("<II", data, METADATA_RAW + 0x304, 2, 4)
    struct.pack_into("<16I", data, METADATA_RAW + 0x30C, *(RUNTIMES + (0,) * 12))
    data.extend(b"\0BeginProfileStateUpdate\0AppendProfileStateChunk\0CommitProfileStateUpdate\0"
                b"GetProfileStateChunkCount\0GetProfileStateChunk\0HasProfileState\0OPENMCM_BROWSER_PROFILE_V1\0")
    return data


class BrowserNativeArtifactTests(unittest.TestCase):
    def test_valid_metadata_is_source_supported_not_game_verified(self):
        result = validate_dll(browser_fixture())
        self.assertEqual(result["plugin"], "OpenMCMBrowser")
        self.assertFalse(result["game_tested"])
        self.assertTrue(result["address_library_required"])

    def test_unlisted_runtime_rejected(self):
        for offset in (0x30C, 0x31C):
            with self.subTest(offset=offset):
                data = browser_fixture()
                struct.pack_into("<I", data, METADATA_RAW + offset, 0x01070700)
                with self.assertRaisesRegex(ValidationError, "allowlist"):
                    validate_dll(data)

    def test_missing_query_export_rejected(self):
        data = browser_fixture()
        struct.pack_into("<I", data, EXPORT_RAW + 24, 2)
        with self.assertRaisesRegex(ValidationError, "SKSEPlugin_Query"):
            validate_dll(data)

    def test_attribution_is_preserved(self):
        data = browser_fixture()
        data[METADATA_RAW + 0x108:METADATA_RAW + 0x208] = bytes(256)
        with self.assertRaisesRegex(ValidationError, "attribution"):
            validate_dll(data)

    def test_unlimited_version_independence_rejected(self):
        data = browser_fixture()
        struct.pack_into("<I", data, METADATA_RAW + 0x308, 5)
        with self.assertRaisesRegex(ValidationError, "unlimited"):
            validate_dll(data)

    def test_foreign_profile_header_rejected(self):
        data = browser_fixture()
        data.extend(b"MCMR_PROFILE_V1\0")
        with self.assertRaisesRegex(ValidationError, "Foreign Redone"):
            validate_dll(data)

    def test_missing_bridge_rejected(self):
        data = bytes(browser_fixture()).replace(b"HasProfileState\0", b"NotProfileState\0")
        with self.assertRaisesRegex(ValidationError, "Missing native profile bridge"):
            validate_dll(data)

    def test_original_chargen_source_is_not_compiled_into_browser(self):
        build = (ROOT / "src/browser-native/xmake.lua").read_text(encoding="utf-8")
        self.assertNotIn("OpenMCMRuntime", build)
        self.assertNotIn("PrecachePatch", build)
        self.assertNotIn("Registry.cpp", build)
        self.assertNotIn("Serialization.cpp", build)


class BrowserSourcePackageTests(unittest.TestCase):
    def test_bundled_dependency_repackages_without_network_or_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "dependencies/source/source.zip"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"complete bundled source")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            with patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network")):
                self.assertEqual(dependency_source(root, "source.zip", "https://invalid.test/source.zip", digest), source.read_bytes())
            self.assertFalse((root / ".tools").exists())

    def test_corrupt_bundled_dependency_does_not_silently_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory, data in (("dependencies/source", b"corrupt"), (".tools/downloads/browser-native-sources", b"good")):
                path = root / directory / "source.zip"
                path.parent.mkdir(parents=True)
                path.write_bytes(data)
            with patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network")):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    dependency_source(root, "source.zip", "https://invalid.test/source.zip", hashlib.sha256(b"good").hexdigest())

    def test_cache_is_verified_and_no_network_needed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cached = root / ".tools/downloads/browser-native-sources/source.zip"
            cached.parent.mkdir(parents=True)
            cached.write_bytes(b"cached source")
            with patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network")):
                self.assertEqual(dependency_source(root, "source.zip", "https://invalid.test/source.zip", hashlib.sha256(b"cached source").hexdigest()), b"cached source")
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    dependency_source(root, "source.zip", "https://invalid.test/source.zip", "0" * 64)

    def test_download_verified_before_caching(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b"downloaded source")):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    dependency_source(root, "source.zip", "https://invalid.test/source.zip", "0" * 64)
            self.assertFalse((root / ".tools").exists())
            with patch("urllib.request.urlopen", return_value=io.BytesIO(b"downloaded source")):
                result = dependency_source(root, "source.zip", "https://invalid.test/source.zip", hashlib.sha256(b"downloaded source").hexdigest())
            self.assertEqual((root / ".tools/downloads/browser-native-sources/source.zip").read_bytes(), result)


if __name__ == "__main__":
    unittest.main()
