"""Preserve release notices and owner-maintained archives, not legal certification."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import package_openmcm_source as packager

BUILD = ROOT / "scripts/Build-OpenMCM.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
NOTICES = ("README.md", "README.txt", "LICENSE", "LICENSE.txt", "THIRD_PARTY_NOTICES.md")
# Full GPL v3 text already verified against CommonLibSSE-NG's COPYING.txt.
# Normalize only CRLF/LF so checkout line endings do not alter this text check.
GPL3_SHA256 = "f817886ee6bb65ed3098a7987b1e9781653d15c71f85589ce0d2af663c66d373"


class CompliancePreservationTests(unittest.TestCase):
    def test_full_unmodified_gpl_text_and_both_license_filenames(self):
        license_bytes = (ROOT / "LICENSE").read_bytes()
        self.assertEqual(license_bytes, (ROOT / "LICENSE.txt").read_bytes())
        normalized = license_bytes.replace(b"\r\n", b"\n")
        self.assertEqual(hashlib.sha256(normalized).hexdigest(), GPL3_SHA256)

    def test_readme_keeps_copyright_grant_warranty_and_component_boundaries(self):
        readme = " ".join((ROOT / "README.txt").read_text(encoding="utf-8").split())
        for notice in (
            "Copyright (C) 2026 TheElderLord1337 and OpenMCM contributors",
            "either version 3 of the License, or (at your option) any later version",
            "WITHOUT ANY WARRANTY",
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE",
            "The GPL notice above applies to original OpenMCM code",
            "licenses/OpenMCM-previous-MIT.txt",
            "component is GPL-3.0-only with its existing attribution",
            "The Field Guide example retains its separate permissive licence",
            "does not relicense Bethesda assets or the optional Jaxonz MCM Kicker adaptations",
            "Those adaptations retain upstream permissions, including their restriction on sale",
        ):
            with self.subTest(notice=notice):
                self.assertIn(notice, readme)
        self.assertTrue((ROOT / "licenses/OpenMCM-previous-MIT.txt").is_file())

    def test_main_build_copies_notices_and_complete_source_before_checksums(self):
        build = BUILD.read_text(encoding="utf-8")
        for name in NOTICES + ("licenses",):
            with self.subTest(name=name):
                self.assertIn(f"Copy-Item -LiteralPath (Join-Path $projectRoot '{name}')", build)
        source_position = build.index("'tools\\package_openmcm_source.py'")
        self.assertLess(source_position, build.index("$checksumPath ="))
        self.assertLess(source_position, build.index("Compress-Archive -Path"))
        self.assertIn("'correspondingSource'", build)
        fomod = (ROOT / "scripts/Build-FomodPackage.ps1").read_text(encoding="utf-8")
        self.assertIn("elseif ($entry.Name -notin @('Data', 'OpenMCM_SHA256SUMS.txt'))", fomod)
        self.assertIn("Copy-Item -LiteralPath $entry.FullName -Destination $outputRoot -Recurse", fomod)

    def test_source_collector_keeps_exact_notice_bytes(self):
        with tempfile.TemporaryDirectory(prefix="openmcm-notices-") as temporary:
            project = Path(temporary)
            for name in packager.REQUIRED_PROJECT_FILES:
                path = project / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"// editable source fixture\n")
            expected = {name: (ROOT / name).read_bytes()
                        for name in NOTICES + ("licenses/OpenMCM-previous-MIT.txt",)}
            for name, content in expected.items():
                (project / name).write_bytes(content)
            collected = packager.project_sources(project)
            for name, content in expected.items():
                with self.subTest(name=name):
                    self.assertEqual(collected[name], content)

    def test_both_archive_publication_checks_refuse_overwrite(self):
        build = BUILD.read_text(encoding="utf-8")
        refusal = 'throw "Refusing to overwrite an existing release archive: $archivePath"'
        self.assertEqual(build.count(refusal), 2)
        self.assertNotIn("Remove-Item -LiteralPath $archivePath", build)
        self.assertLess(build.rindex(refusal), build.index("Compress-Archive -Path"))


@unittest.skipUnless(POWERSHELL, "PowerShell required to execute release archive guard")
class ExistingReleaseArchiveTests(unittest.TestCase):
    def test_existing_archive_rejected_before_tools_or_staging_and_bytes_preserved(self):
        for package_format, suffix in (("Fomod", "-FOMOD"), ("Standalone", "")):
            with self.subTest(package_format=package_format):
                with tempfile.TemporaryDirectory(prefix="openmcm-release-guard-") as temporary:
                    project = Path(temporary)
                    build = project / "scripts/Build-OpenMCM.ps1"
                    build.parent.mkdir()
                    shutil.copyfile(BUILD, build)
                    archive = project / "dist" / f"OpenMCM-2.1.0{suffix}.zip"
                    archive.parent.mkdir()
                    original = b"Owner-maintained published archive; do not replace.\r\n"
                    archive.write_bytes(original)
                    result = subprocess.run(
                        [POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive",
                         "-ExecutionPolicy", "Bypass", "-File", str(build),
                         "-Version", "2.1.0", "-PackageFormat", package_format],
                        capture_output=True, text=True, timeout=30)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Refusing to overwrite an existing release archive",
                                  result.stdout + result.stderr)
                    self.assertEqual(archive.read_bytes(), original)
                    self.assertFalse((project / ".tools").exists())
                    self.assertFalse((project / "build").exists())
                    self.assertEqual({path.relative_to(project).as_posix()
                                      for path in project.rglob("*") if path.is_file()},
                                     {"scripts/Build-OpenMCM.ps1", archive.relative_to(project).as_posix()})


if __name__ == "__main__":
    unittest.main()
