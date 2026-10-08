"""Build wiring and executable Caprica identifier-repair regressions."""
from __future__ import annotations

import base64
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "tests"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from check_mcm_contract import _parse_skyrim_pex_envelope  # noqa: E402
from test_contract_checker import _minimal_pex  # noqa: E402

BUILD = ROOT / "scripts/Build-OpenMCM.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def run_repair(directory: Path) -> subprocess.CompletedProcess:
    script = r"""
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$tokens = $null
$errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile('__BUILD__', [ref]$tokens, [ref]$errors)
if ($errors.Count -ne 0) { throw 'Build script failed parsing' }
$helper = $ast.Find({ param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq 'Convert-CapricaSkyUIIdentifiers'
}, $true)
if ($null -eq $helper) { throw 'Identifier helper missing' }
. ([scriptblock]::Create($helper.Extent.Text))
Convert-CapricaSkyUIIdentifiers -Path '__INPUT__'
"""
    script = script.replace("__BUILD__", str(BUILD).replace("'", "''"))
    script = script.replace("__INPUT__", str(directory).replace("'", "''"))
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return subprocess.run([POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive",
                           "-EncodedCommand", encoded], capture_output=True, text=True, timeout=30)


class PapyrusExtensionBuildWiringTests(unittest.TestCase):
    def test_both_examples_compile_outside_installed_scripts(self):
        build = BUILD.read_text(encoding="utf-8")
        self.assertIn("examples\\OpenMCMExample.psc", build)
        self.assertIn("examples\\OpenMCMApiExample.psc", build)
        self.assertIn("foreach ($exampleSource in $exampleSources)", build)
        self.assertIn('"--output=$exampleOutput"', build)
        self.assertIn("Convert-CapricaSkyUIIdentifiers -Path $exampleOutput", build)
        self.assertIn("Opt-in API example PEX must reference canonical OpenMCM_ConfigBase", build)
        self.assertIn("Copy-Item -LiteralPath (Join-Path $projectRoot 'examples')", build)

    def test_coexist_allowlist_copies_both_api_sources_and_pex(self):
        build = (ROOT / "scripts/Build-FomodPackage.ps1").read_text(encoding="utf-8")
        for script in ("OpenMCM", "OpenMCM_ConfigBase"):
            self.assertIn(f"'Scripts\\{script}.pex'", build)
            self.assertIn(f"'Source\\Scripts\\{script}.psc'", build)
        self.assertIn("tools\\check_openmcm_api.py", build)

    def test_staging_and_standalone_zip_require_new_api(self):
        build = BUILD.read_text(encoding="utf-8")
        self.assertIn("'tools\\check_openmcm_api.py') $stagingRoot", build)
        self.assertIn("'tools\\check_openmcm_api.py') $archivePath", build)
        self.assertIn("'2.1.0'", (ROOT / "build.ps1").read_text(encoding="utf-8"))

    def test_api_docs_and_prerelease_metadata_ship(self):
        build = BUILD.read_text(encoding="utf-8")
        self.assertIn("'docs\\OpenMCM-API.md'", build)
        self.assertIn("OpenMCM_API = [ordered]@{", build)
        self.assertIn("version = 1", build)
        self.assertIn("prerelease = $true", build)


@unittest.skipUnless(POWERSHELL, "PowerShell required to execute build helper")
class CapricaIdentifierRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "Probe.pex"

    def test_repairs_canonical_types_only_preserving_lengths_metadata_and_literals(self):
        symbols = {"sKI_ConfigBase", "sKI_ConfigBase[]", "openMCM", "openMCM_ConfigBase",
                   "openMCM_ConfigBase[]", "OpenMCM_ConfigBase",
                   "prefix sKI_ConfigBase[] suffix", "prefix openMCM_ConfigBase suffix"}
        before = _minimal_pex(symbols, "Probe", "sKI_ConfigBase").replace(b"Probe.psc", b"sKI__.psc")
        self.path.write_bytes(before)
        result = run_repair(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "5")
        after = self.path.read_bytes()
        self.assertEqual(len(before), len(after))
        strings, objects = _parse_skyrim_pex_envelope(after)
        self.assertEqual(objects, ["Probe"])
        for expected in ("SKI_ConfigBase", "SKI_ConfigBase[]", "OpenMCM", "OpenMCM_ConfigBase",
                         "OpenMCM_ConfigBase[]", "prefix sKI_ConfigBase[] suffix",
                         "prefix openMCM_ConfigBase suffix"):
            self.assertIn(expected, strings)
        self.assertIn(b"sKI__.psc", after)  # source metadata is not a reference
        self.assertEqual(sum(a != b for a, b in zip(before, after)), 5)
        repeat = run_repair(self.root)
        self.assertEqual(repeat.returncode, 0, repeat.stderr)
        self.assertEqual(repeat.stdout.strip(), "0")
        self.assertEqual(self.path.read_bytes(), after)

    def test_invalid_or_truncated_pex_is_rejected_without_writes(self):
        valid = _minimal_pex({"openMCM_ConfigBase"}, "Probe", "Quest")
        for raw in (b"sKI_ConfigBase openMCM_ConfigBase", valid[:17], valid[:30]):
            with self.subTest(length=len(raw)):
                self.path.write_bytes(raw)
                result = run_repair(self.root)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.path.read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
