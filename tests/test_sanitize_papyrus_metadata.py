from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for folder in (ROOT / "tools", ROOT / "tests"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import sanitize_papyrus_metadata as sanitizer  # noqa: E402
from check_mcm_contract import _parse_skyrim_pex_envelope  # noqa: E402
from test_contract_checker import _minimal_pex  # noqa: E402


def _string(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return struct.pack(">H", len(encoded)) + encoded


def _metadata_and_tail(data: bytes) -> tuple[list[str], bytes]:
    offset = 16
    values = []
    for _ in range(3):
        size = struct.unpack_from(">H", data, offset)[0]
        offset += 2
        values.append(data[offset:offset + size].decode("utf-8"))
        offset += size
    return values, data[offset:]


def _fixture(source: str = r"C:\PrivateBuilder\workspace\Example.psc") -> bytes:
    # Use a coherent PEX envelope with real string-table/object boundaries.
    minimal = _minimal_pex({"Example", "Quest", "OnInit", "PrivateBuilder"}, "Example", "Quest")
    _, tail = _metadata_and_tail(minimal)
    timestamp = struct.pack(">Q", 1_777_654_321)
    return (minimal[:8] + timestamp + _string(source)
            + _string("PrivateBuilder") + _string("PRIVATE-WORKSTATION") + tail)


class SanitizePapyrusMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_only_three_metadata_fields_change(self):
        original = _fixture()
        sanitized = sanitizer.sanitize_bytes(original)
        before_values, before_tail = _metadata_and_tail(original)
        after_values, after_tail = _metadata_and_tail(sanitized)
        self.assertEqual(after_values, ["Example.psc", "OpenMCM", "Build"])
        self.assertNotEqual(before_values, after_values)
        self.assertEqual(sanitized[:16], original[:16], "Version, game and timestamp must survive")
        self.assertEqual(after_tail, before_tail, "String table and object bytecode must not change")
        self.assertEqual(_parse_skyrim_pex_envelope(sanitized), _parse_skyrim_pex_envelope(original))
        # Identical text in the runtime string table is NOT compiler metadata.
        self.assertIn(b"PrivateBuilder", after_tail)

    def test_forward_slash_unicode_basename_and_idempotence(self):
        sanitized = sanitizer.sanitize_bytes(_fixture("/private/build/Exemple\u00e9.psc"))
        self.assertEqual(_metadata_and_tail(sanitized)[0], ["Exemple\u00e9.psc", "OpenMCM", "Build"])
        self.assertEqual(sanitizer.sanitize_bytes(sanitized), sanitized)

    def test_rejects_unsafe_or_missing_source_basename(self):
        for name in ("", ".", "..", "C:/folder/", "name:stream", "bad\x00name.psc", "bad\nname.psc"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                sanitizer.sanitize_bytes(_fixture(name))

    def test_rejects_malformed_envelopes(self):
        valid = _fixture()
        # Corrupt UTF-8 in source metadata while keeping its encoded length.
        bad_utf8 = valid[:18] + b"\xff" + valid[19:]
        for data in (b"", b"BAD!" + valid[4:], valid[:17], valid[:-1], valid + b"extra", bad_utf8):
            with self.subTest(length=len(data)), self.assertRaises(ValueError):
                sanitizer.sanitize_bytes(data)

    def test_bytes_size_bound(self):
        valid = _fixture()
        with mock.patch.object(sanitizer, "MAX_PEX_BYTES", len(valid) - 1):
            with self.assertRaisesRegex(ValueError, "size bound"):
                sanitizer.sanitize_bytes(valid)

    def test_single_file_and_already_normalized_file(self):
        path = self.root / "Example.pex"
        path.write_bytes(_fixture())
        self.assertEqual(sanitizer.sanitize_path(path), 1)
        expected = path.read_bytes()
        self.assertEqual(_metadata_and_tail(expected)[0], ["Example.psc", "OpenMCM", "Build"])
        with mock.patch.object(Path, "write_bytes", side_effect=AssertionError("Unchanged input must not be rewritten")):
            self.assertEqual(sanitizer.sanitize_path(path), 1)
        self.assertEqual(path.read_bytes(), expected)

    def test_bad_later_file_leaves_all_inputs_unchanged(self):
        good = self.root / "a-valid.pex"
        bad = self.root / "z-invalid.pex"
        original = _fixture()
        malformed = b"not a PEX"
        good.write_bytes(original)
        bad.write_bytes(malformed)
        with self.assertRaises(ValueError):
            sanitizer.sanitize_path(self.root)
        self.assertEqual(good.read_bytes(), original)
        self.assertEqual(bad.read_bytes(), malformed)

    def test_directory_only_processes_direct_pex_children(self):
        direct = self.root / "Example.pex"
        nested_dir = self.root / "nested"
        nested_dir.mkdir()
        nested = nested_dir / "Other.pex"
        unrelated = self.root / "notes.txt"
        original = _fixture()
        direct.write_bytes(original)
        nested.write_bytes(original)
        unrelated.write_bytes(b"not a PEX")
        self.assertEqual(sanitizer.sanitize_path(self.root), 1)
        self.assertNotEqual(direct.read_bytes(), original)
        self.assertEqual(nested.read_bytes(), original)
        self.assertEqual(unrelated.read_bytes(), b"not a PEX")

    def test_empty_directory_missing_and_wrong_extension_rejected(self):
        text_path = self.root / "Example.txt"
        text_path.write_bytes(_fixture())
        for target in (self.root, self.root / "missing.pex", text_path):
            with self.subTest(target=target), self.assertRaises(ValueError):
                sanitizer.sanitize_path(target)

    def test_file_count_bound_validates_before_writes(self):
        original = _fixture()
        paths = [self.root / f"{index}.pex" for index in range(3)]
        for path in paths:
            path.write_bytes(original)
        with mock.patch.object(sanitizer, "MAX_FILES", 2), self.assertRaises(ValueError):
            sanitizer.sanitize_path(self.root)
        self.assertTrue(all(path.read_bytes() == original for path in paths))

    def test_file_size_bound_validates_before_writes(self):
        original = _fixture()
        path = self.root / "Example.pex"
        path.write_bytes(original)
        with mock.patch.object(sanitizer, "MAX_PEX_BYTES", len(original) - 1):
            with self.assertRaisesRegex(ValueError, "bounded regular PEX"):
                sanitizer.sanitize_path(path)
        self.assertEqual(path.read_bytes(), original)

    def test_target_link_rejected_before_traversal(self):
        with mock.patch.object(Path, "is_symlink", return_value=True):
            with mock.patch.object(Path, "glob", side_effect=AssertionError("Must not traverse a link")):
                with self.assertRaisesRegex(ValueError, "must not be a link"):
                    sanitizer.sanitize_path(self.root)

    def test_link_child_rejected_without_modifying_prior_child(self):
        good = self.root / "a-valid.pex"
        linked = self.root / "z-link.pex"
        original = _fixture()
        good.write_bytes(original)
        linked.write_bytes(original)
        # Simulate the filesystem link predicate portably, including Windows
        # systems whose user cannot create symlinks without elevation.
        with mock.patch.object(Path, "is_symlink", autospec=True, side_effect=lambda path: path == linked):
            with self.assertRaisesRegex(ValueError, "bounded regular PEX"):
                sanitizer.sanitize_path(self.root)
        self.assertEqual(good.read_bytes(), original)
        self.assertEqual(linked.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
