"""Run the real .NET Nexus preprocessing regression against temporary ZIPs.

No installed game/mod-manager files are used. This intentionally checks the
UTF-16BE StringStream path, not only XML syntax or schema validity.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_fomod_installer import create_module_config, write_installer_xml  # noqa: E402

POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")
VALIDATOR = ROOT / "scripts/Test-FomodXml.ps1"
XML_FILES = ("fomod/ModuleConfig.xml", "fomod/info.xml")
OLD_DECLARATION = b"<?xml version='1.0' encoding='utf-8'?>"
UNICODE_DESCRIPTION = "Skyrim's menus - café, 日本語, colours & a player's choices."


@unittest.skipUnless(POWERSHELL, "PowerShell required for .NET FOMOD reader regression")
class FomodXmlReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="openmcm-xml-reader-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "temporary FOMOD.zip"

    def proper_xml(self, newline: bytes = b"\n") -> dict[str, bytes]:
        module = create_module_config("1.2.0-alpha.3", include_native=True)
        module.getroot().find(".//plugin/description").text = UNICODE_DESCRIPTION
        info = ET.Element("fomod")
        ET.SubElement(info, "Name").text = "OpenMCM"
        ET.SubElement(info, "Version").text = "1.2.0-alpha.3"
        ET.SubElement(info, "Description").text = UNICODE_DESCRIPTION
        ET.indent(info, space="  ")
        payload = {}
        for relative, tree in zip(XML_FILES, (module, ET.ElementTree(info))):
            output = self.root / Path(relative).name
            write_installer_xml(tree, output)
            raw = output.read_bytes().replace(b"\r\n", b"\n")
            payload[relative] = raw.replace(b"\n", newline)
        return payload

    def run_archive(self, payload: dict[str, bytes], *, extra: tuple[str, bytes] | None = None):
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, raw in payload.items():
                archive.writestr(name, raw)
            if extra is not None:
                archive.writestr(*extra)
        return subprocess.run(
            [POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive", "-File", str(VALIDATOR),
             "-ArchivePath", str(self.archive)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )

    @staticmethod
    def output(result) -> str:
        return result.stdout + result.stderr

    def test_generated_xml_passes_with_lf_crlf_unicode_and_apostrophes(self):
        for newline in (b"\n", b"\r\n"):
            with self.subTest(newline=newline):
                payload = self.proper_xml(newline)
                for raw in payload.values():
                    self.assertTrue(raw.startswith(b'<?xml version="1.0" encoding="utf-8"?>'))
                    text = raw.decode("utf-8")
                    self.assertIn("Skyrim's menus", text)
                    self.assertIn("a player's choices", text)
                    self.assertIn("café, 日本語", text)
                    self.assertIn("&amp;", text)
                result = self.run_archive(payload)
                self.assertEqual(result.returncode, 0, self.output(result))
                self.assertIn("PASS FOMOD preprocessing self-check", result.stdout)
                self.assertIn("PASS both FOMOD XML files", result.stdout)
                for relative in XML_FILES:
                    self.assertIn("PASS Nexus XML preprocessing: " + relative, result.stdout)

    def test_old_single_quoted_header_fails_independently_in_either_xml(self):
        for bad_file in XML_FILES:
            for newline in (b"\n", b"\r\n"):
                with self.subTest(file=bad_file, newline=newline):
                    payload = self.proper_xml(newline)
                    # Independently construct the old declaration, rather than
                    # reusing the production serializer under test.
                    root_tag = b"config" if bad_file.endswith("ModuleConfig.xml") else b"fomod"
                    payload[bad_file] = OLD_DECLARATION + newline + b"<" + root_tag + b" />"
                    result = self.run_archive(payload)
                    self.assertNotEqual(result.returncode, 0, self.output(result))
                    self.assertIn("PASS FOMOD preprocessing self-check", result.stdout)
                    self.assertIn(bad_file + ":", self.output(result))
                    self.assertIn("0x00", self.output(result))
                    self.assertRegex(self.output(result), r"Line 1,\s*position 39")
                    other_file = next(name for name in XML_FILES if name != bad_file)
                    self.assertIn("PASS Nexus XML preprocessing: " + other_file, result.stdout)

    def test_missing_either_xml_entry_is_rejected(self):
        for missing in XML_FILES:
            with self.subTest(missing=missing):
                payload = self.proper_xml()
                del payload[missing]
                result = self.run_archive(payload)
                self.assertNotEqual(result.returncode, 0, self.output(result))
                self.assertIn("Expected exactly one '" + missing + "'", self.output(result))
                self.assertIn("found 0", self.output(result))

    def test_case_insensitive_duplicate_either_xml_entry_is_rejected(self):
        for duplicate in XML_FILES:
            with self.subTest(duplicate=duplicate):
                payload = self.proper_xml()
                result = self.run_archive(payload, extra=(duplicate.upper(), payload[duplicate]))
                self.assertNotEqual(result.returncode, 0, self.output(result))
                self.assertIn("Expected exactly one '" + duplicate + "'", self.output(result))
                self.assertIn("found 2", self.output(result))

    def test_malformed_xml_fails_instead_of_only_checking_declarations(self):
        payload = self.proper_xml()
        payload[XML_FILES[0]] = b'<?xml version="1.0" encoding="utf-8"?>\n<config><broken></config>'
        result = self.run_archive(payload)
        self.assertNotEqual(result.returncode, 0, self.output(result))
        self.assertIn(XML_FILES[0] + ":", self.output(result))
        self.assertNotIn("PASS both FOMOD XML files", result.stdout)


if __name__ == "__main__":
    unittest.main()
