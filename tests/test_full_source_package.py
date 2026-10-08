"""Full-source package scope and integrity; not legal or in-game certification."""
from __future__ import annotations

import hashlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import package_openmcm_source as packager


class FullSourcePackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "project"
        self.root.mkdir()
        self.output = Path(self.temporary.name) / "source.zip"
        self.browser_path = Path(self.temporary.name) / "browser.zip"
        dependency = io.BytesIO()
        with zipfile.ZipFile(dependency, "w") as source:
            source.writestr("example/LICENSE", "Test fixture license\n")
            source.writestr("example/source.h", "// Test fixture source\n")
        self.dependency = dependency.getvalue()
        self.pins = (("example-1.0.zip", "https://example.invalid/source.zip",
                      hashlib.sha256(self.dependency).hexdigest()),)
        dependency_patch = patch.object(packager, "DEPENDENCIES", self.pins)
        dependency_patch.start()
        self.addCleanup(dependency_patch.stop)
        for name in packager.ROOT_FILES:
            self.write(name)
        for name in (
            "src/actionscript/ConfigPanel.as", "src/papyrus/SKI_ConfigBase.psc",
            "src/native/OpenMCMRuntime.cpp", "src/browser-native/Bridge.cpp",
            "src/browser-native/xmake.lua", "src/browser-native/LICENSE-GPL-3.0.txt",
            "src/plugin/SkyUI_SE.esp/RecordData.yaml",
            "src/plugin-coexist/OpenMCM.esp/RecordData.yaml",
            "src/translations/SkyUI_SE_ENGLISH.tsv", "src/compat/jaxonz-kicker/Kicker.psc",
            "scripts/Build-OpenMCM.ps1", "vendor/papyrus-stubs/Quest.psc",
            "vendor/papyrus-stubs/TESV_Papyrus_Flags.flg", "tests/test_example.py",
            "examples/field-guide/plugin/OpenMCM_FieldGuide.esp/RecordData.yaml",
            "examples/field-guide/LICENSE", "docs/OpenMCM-API.md", "release/version-notes.md",
            "licenses/OpenMCM-previous-MIT.txt",
        ):
            self.write(name)
        self.browser = {name: b"// Test fixture source\n" for name in packager.BROWSER_SUPPORT_FILES}
        for name in self.browser:
            self.write(name, self.browser[name])
        for name in ("src/browser-native/Bridge.cpp", "src/browser-native/xmake.lua",
                     "src/browser-native/LICENSE-GPL-3.0.txt"):
            self.browser[name] = (self.root / name).read_bytes()
        for name in ("xmake.lua", "include/SKSE/Version.h", "COPYING.txt", "EXCEPTIONS.md"):
            self.browser[packager.COMMONLIB_PREFIX + name] = b"// Test fixture dependency\n"
        self.browser[packager.COMMONLIB_PREFIX + "tests/REL/version-invalid-format.bin"] = b"\0\1\2\3"
        self.browser["dependencies/source/example-1.0.zip"] = self.dependency
        self.browser["licenses/example-LICENSE.txt"] = b"Test fixture license\n"
        self.browser["BUILD-SOURCE.txt"] = b"Browser build instructions\n"
        self.browser["DEPENDENCIES.json"] = json.dumps({
            "commonlib": {"version": "7.5.1", "commit": packager.COMMONLIB_COMMIT},
            "source_archives": [{"file": name, "url": url, "sha256": digest}
                                for name, url, digest in self.pins],
        }).encode()
        self.make_browser()

    def write(self, name, data=b"// Test fixture editable source\n"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def make_browser(self, extra=None, manifest=True):
        files = dict(self.browser)
        if extra:
            files.update(extra)
        if manifest:
            files["SHA256SUMS.txt"] = "".join(
                f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(files.items())
            ).encode()
        with zipfile.ZipFile(self.browser_path, "w") as source:
            for name, data in files.items():
                source.writestr(name, data)

    def package(self):
        packager.package(self.root, self.browser_path, self.output, "2.0.1-rc.3")

    def test_includes_editable_components_and_complete_browser_bundle(self):
        self.package()
        validated = packager.validate_source_archive(self.output.read_bytes())
        with zipfile.ZipFile(self.output) as result:
            names = set(result.namelist())
            self.assertEqual(set(validated), names)
            self.assertIn("src/plugin/SkyUI_SE.esp/RecordData.yaml", names)
            self.assertIn("src/plugin-coexist/OpenMCM.esp/RecordData.yaml", names)
            self.assertIn("examples/field-guide/plugin/OpenMCM_FieldGuide.esp/RecordData.yaml", names)
            for path in self.root.rglob("*"):
                if path.is_file():
                    self.assertEqual(result.read(path.relative_to(self.root).as_posix()), path.read_bytes())
            with zipfile.ZipFile(self.browser_path) as original:
                for name in original.namelist():
                    merged = "source-manifests/browser/" + name if name in {"BUILD-SOURCE.txt", "SHA256SUMS.txt"} else name
                    self.assertEqual(result.read(merged), original.read(name))
            manifest = result.read("SHA256SUMS.txt").decode().splitlines()
            self.assertEqual(len(manifest), len(names) - 1)
            for line in manifest:
                digest, name = line.split("  ", 1)
                self.assertEqual(hashlib.sha256(result.read(name)).hexdigest(), digest)
            instructions = result.read("BUILD-SOURCE.txt").decode()
            self.assertIn("Supply your own lawful Skyrim", instructions)
            self.assertIn("not a legal compliance certificate", instructions)
            self.assertIn("not an offline xmake package cache", instructions)
            self.assertEqual(result.read("dependencies/source/example-1.0.zip"), self.dependency)

    def test_excludes_outputs_assets_environment_and_diagnostics(self):
        excluded = (
            "build/personal.txt", "dist/prior.zip", ".tools/secrets.txt", "package/Data/source.psc",
            "src/build/generated.cpp", "src/.git/config", "src/__pycache__/cache.py",
            "src/native/plugin.dll", "src/plugin/final.esp", "src/papyrus/final.pex",
            "src/actionscript/final.swf", "scripts/helper.exe", "tests/dumps/crash.txt",
            "tools/diagnostics/player.json", "docs/diagnostics/session.md", "docs/assets/image.txt",
            "release/cover.png", "release/old.zip", "tools/.env", "src/environment.env",
        )
        for name in excluded:
            self.write(name, b"sensitive fixture")
        self.package()
        with zipfile.ZipFile(self.output) as result:
            self.assertFalse(set(excluded).intersection(result.namelist()))

    def test_deterministic_archive(self):
        self.package()
        first = self.output.read_bytes()
        for path in self.root.rglob("*"):
            if path.is_file():
                os.utime(path, (1234567890, 1234567890))
        self.package()
        self.assertEqual(first, self.output.read_bytes())

    def test_missing_required_source_or_license_rejected(self):
        for name in ("LICENSE", "src/native/OpenMCMRuntime.cpp"):
            with self.subTest(name=name):
                original = (self.root / name).read_bytes()
                (self.root / name).unlink()
                with self.assertRaisesRegex(ValueError, "missing"):
                    self.package()
                self.write(name, original)

    def test_binary_disguised_as_source_rejected(self):
        self.write("tools/payload.py", b"MZ\0executable")
        with self.assertRaisesRegex(ValueError, "Non-text"):
            self.package()

    def test_browser_traversal_and_windows_path_aliases_rejected(self):
        for name in ("../escape.txt", "/absolute.txt", "C:/escape.txt", "src\\escape.txt",
                     "src/./escape.txt", "src//escape.txt", "src/../escape.txt",
                     "src/trailing./escape.txt", "src/con.txt", "src/escape.txt:stream"):
            with self.subTest(name=name):
                self.make_browser({name: b"unsafe"})
                with self.assertRaisesRegex(ValueError, "Unsafe archive path"):
                    self.package()

    def test_missing_manifest_or_unlisted_member_rejected(self):
        self.make_browser(manifest=False)
        with self.assertRaisesRegex(ValueError, "manifest is missing"):
            self.package()
        self.make_browser()
        with zipfile.ZipFile(self.browser_path, "a") as source:
            source.writestr("src/browser-native/unlisted.cpp", "unlisted")
        with self.assertRaisesRegex(ValueError, "manifest does not match"):
            self.package()

    def test_browser_manifest_checksum_mismatch_rejected(self):
        self.make_browser({"SHA256SUMS.txt": b"bad"}, manifest=False)
        with self.assertRaisesRegex(ValueError, "Invalid browser source manifest"):
            self.package()
        self.make_browser()
        with zipfile.ZipFile(self.browser_path) as source:
            files = {name: source.read(name) for name in source.namelist()}
        files["src/browser-native/Bridge.cpp"] = b"Changed source\n"
        with zipfile.ZipFile(self.browser_path, "w") as source:
            for name, data in files.items():
                source.writestr(name, data)
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.package()

    def test_pinned_nested_dependency_mismatch_rejected(self):
        self.make_browser({"dependencies/source/example-1.0.zip": b"changed nested archive"})
        with self.assertRaisesRegex(ValueError, "Pinned dependency source checksum mismatch"):
            self.package()

    def test_browser_binary_or_environment_payload_rejected(self):
        for name in (".tools/compiler.exe", "src/browser-native/plugin.dll",
                     ".tools/CommonLibSSE-NG-7.5.1/build/generated.cpp", "docs/diagnostics/private.txt"):
            with self.subTest(name=name):
                self.make_browser({name: b"unwanted payload"})
                with self.assertRaisesRegex(ValueError, "Unexpected browser source member"):
                    self.package()

    def test_different_source_collision_rejected(self):
        self.write("src/browser-native/Bridge.cpp", b"A different release\n")
        with self.assertRaisesRegex(ValueError, "Source collision"):
            self.package()

    def test_case_colliding_browser_members_rejected(self):
        self.make_browser({"src/browser-native/bridge.cpp": b"duplicate case"})
        with self.assertRaisesRegex(ValueError, "case-colliding"):
            self.package()

    def test_browser_symlink_rejected(self):
        self.make_browser({"src/browser-native/link.cpp": b"outside.cpp"})
        with zipfile.ZipFile(self.browser_path) as source:
            files = [(item, source.read(item)) for item in source.infolist()]
        with zipfile.ZipFile(self.browser_path, "w") as source:
            for item, data in files:
                if item.filename.endswith("link.cpp"):
                    item.create_system = 3
                    item.external_attr = (stat.S_IFLNK | 0o777) << 16
                source.writestr(item, data)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.package()

    def test_project_symlink_rejected(self):
        link = self.root / "src/papyrus/link.psc"
        try:
            link.symlink_to(self.root / "README.md")
        except OSError:
            self.skipTest("Host does not allow creating symlinks")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.package()

    def test_failed_input_preserves_existing_output(self):
        self.output.write_bytes(b"existing archive")
        self.make_browser({"src/browser-native/Bridge.cpp": b"conflicting source"})
        with self.assertRaisesRegex(ValueError, "Source collision"):
            self.package()
        self.assertEqual(self.output.read_bytes(), b"existing archive")

    def test_full_archive_validator_detects_modified_content(self):
        self.package()
        with zipfile.ZipFile(self.output) as source:
            files = {name: source.read(name) for name in source.namelist()}
        files["src/actionscript/ConfigPanel.as"] = b"changed source"
        altered = io.BytesIO()
        with zipfile.ZipFile(altered, "w") as target:
            for name, data in files.items():
                target.writestr(name, data)
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            packager.validate_source_archive(altered.getvalue())

    def test_full_archive_validator_binds_to_release_metadata(self):
        self.package()
        raw = self.output.read_bytes()
        browser_digest = hashlib.sha256(self.browser_path.read_bytes()).hexdigest()
        self.assertTrue(packager.validate_source_archive(raw, version="2.0.1-rc.3", browser_sha256=browser_digest.upper()))
        with self.assertRaisesRegex(ValueError, "version does not match"):
            packager.validate_source_archive(raw, version="2.0.0")
        with self.assertRaisesRegex(ValueError, "browser checksum does not match"):
            packager.validate_source_archive(raw, browser_sha256="0" * 64)

    def test_full_archive_validator_detects_unexpected_binary_even_with_manifest(self):
        self.package()
        with zipfile.ZipFile(self.output) as source:
            files = {name: source.read(name) for name in source.namelist() if name != "SHA256SUMS.txt"}
        files["src/native/unexpected.dll"] = b"MZunexpected binary"
        files["SHA256SUMS.txt"] = "".join(
            f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(files.items())
        ).encode()
        altered = io.BytesIO()
        with zipfile.ZipFile(altered, "w") as target:
            for name, data in files.items():
                target.writestr(name, data)
        with self.assertRaisesRegex(ValueError, "Unexpected full-source member"):
            packager.validate_source_archive(altered.getvalue())


if __name__ == "__main__":
    unittest.main()
