"""Exercise native release version packing without running a compiler/build."""

from __future__ import annotations

import base64
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/Build-NativeRuntime.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def evaluate_versions(versions: list[str]) -> list[dict]:
    # Parse just the named helper's AST: dot-sourcing the full build script
    # would locate Visual Studio, clear outputs and compile the plugin.
    script = r"""
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$buildPath = '__BUILD_PATH__'
$parseTokens = $null
$parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($buildPath, [ref]$parseTokens, [ref]$parseErrors)
if ($parseErrors.Count -ne 0) { throw 'Build script failed to parse.' }
$functionAst = $ast.Find({ param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq 'ConvertTo-OpenMCMPluginVersion'
}, $true)
if ($null -eq $functionAst) { throw 'Native version helper is missing.' }
. ([scriptblock]::Create($functionAst.Extent.Text))
$versions = ConvertFrom-Json '__VERSIONS__'
$results = foreach ($value in $versions) {
    try {
        $packed = ConvertTo-OpenMCMPluginVersion -ReleaseVersion $value
        [pscustomobject]@{ version = $value; packed = $packed; define = ('0x{0:X8}' -f $packed) }
    } catch {
        [pscustomobject]@{ version = $value; error = $_.Exception.Message }
    }
}
ConvertTo-Json -InputObject @($results) -Compress
"""
    script = script.replace("__BUILD_PATH__", str(BUILD).replace("'", "''"))
    script = script.replace("__VERSIONS__", json.dumps(versions).replace("'", "''"))
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        [POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
        check=True, capture_output=True, text=True, timeout=30,
    )
    return json.loads(result.stdout)


class NativeBuildVersionSourceTests(unittest.TestCase):
    def test_both_version_defines_reach_compiler_and_export(self):
        build = BUILD.read_text(encoding="utf-8")
        batch = (ROOT / "scripts/Build-NativeRuntime.cmd").read_text(encoding="utf-8")
        source = (ROOT / "src/native/OpenMCMRuntime.cpp").read_text(encoding="utf-8")
        self.assertIn("$nativeBuildRoot $Version $nativePluginVersionDefine 2>&1", build)
        self.assertIn('/DOPENMCM_VERSION_STRING=\\"%~4\\"', batch)
        self.assertIn('/DOPENMCM_VERSION_PACKED=%~5', batch)
        self.assertIn('if "%~5"=="" exit /b 2', batch)
        self.assertRegex(source, r"SKSEPlugin_Version\s*=\s*\{\s*1,\s*OPENMCM_VERSION_PACKED,")
        self.assertIn('Log("OpenMCMRuntime " OPENMCM_VERSION_STRING', source)
        self.assertLess(build.index("$nativePluginVersion = ConvertTo-OpenMCMPluginVersion"),
                        build.index("Remove-Item -LiteralPath $generatedPath"))

    def test_fallback_string_and_numeric_metadata_match_release(self):
        source = (ROOT / "src/native/OpenMCMRuntime.cpp").read_text(encoding="utf-8")
        release = re.search(r'#define OPENMCM_VERSION_STRING "(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)"', source)
        packed = re.search(r'#define OPENMCM_VERSION_PACKED (0x[0-9A-Fa-f]+)u', source)
        self.assertIsNotNone(release)
        self.assertIsNotNone(packed)
        major, minor, patch = map(int, release.group(1).split('-')[0].split('.'))
        build_default = re.search(r"\$Version\s*=\s*'([^']+)'",
                                  (ROOT / 'build.ps1').read_text(encoding='utf-8'))
        self.assertEqual(release.group(1), build_default.group(1))
        self.assertEqual(int(packed.group(1), 16), major << 24 | minor << 16 | patch << 4)


@unittest.skipUnless(POWERSHELL, "PowerShell required to execute native version helper")
class NativeBuildVersionExecutionTests(unittest.TestCase):
    def test_releases_and_prereleases_use_conventional_skse_packing(self):
        results = evaluate_versions(["1.1.0", "1.1.0-rc.8", "1.0.1-rc.8", "2.3.1", "0.0.1", "2.0.0"])
        self.assertEqual([item["packed"] for item in results],
                         [0x01010000, 0x01010000, 0x01000010, 0x02030010, 0x00000010, 0x02000000])
        self.assertEqual(results[0]["define"], "0x01010000")

    def test_unsigned_boundaries_do_not_overflow_or_change_sign(self):
        results = evaluate_versions(["127.255.4095", "128.0.0", "255.255.4095"])
        self.assertEqual([item["packed"] for item in results],
                         [0x7FFFFFF0, 0x80000000, 0xFFFFFFF0])
        self.assertEqual(results[-1]["define"], "0xFFFFFFF0")

    def test_invalid_versions_fail_instead_of_truncating(self):
        versions = ["0.0.0", "256.0.0", "1.256.0", "1.1.4096", "1.1", "1.1.0.1",
                    "1.1.0+meta", "-1.0.0", "1.1.0&echo", "999999999999999999999999.1.0"]
        results = evaluate_versions(versions)
        self.assertTrue(all("error" in item for item in results), results)


if __name__ == "__main__":
    unittest.main()
