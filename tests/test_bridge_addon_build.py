"""Build boundaries and no-overwrite behavior for the separate Bridge add-on."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts/Build-MCMBridgeAddon.ps1"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


class BridgeAddonBuildTests(unittest.TestCase):
    def test_compiler_uses_adapter_and_pinned_bridge_not_original_host(self):
        script = BUILD.read_text(encoding="utf-8")
        compiler = script.split("& $Caprica --game=skyrim", 1)[1].split("if ($LASTEXITCODE", 1)[0]
        for directory in ("$adapterRoot", "$bridgeHost", "$bridgeNative", "$compileImports", "$stubs"):
            self.assertIn(f'"--import={directory}"', compiler)
        self.assertNotIn("src\\papyrus", compiler)
        self.assertIn("foreach ($script in @('OpenMCM', 'OpenMCM_ConfigBase'))", script)
        self.assertIn("'tools\\sanitize_papyrus_metadata.py') $pex", script)
        self.assertIn("'tools\\repair_papyrus_identifiers.py') $pex", script)

    def test_rebuild_inputs_and_addon_metadata_are_explicit(self):
        script = BUILD.read_text(encoding="utf-8")
        for token in ("'upstream\\mcm-bridge'", "'upstream.json'", "$expectedImports",
                      "'c039e67e9455ab9b21ba3024d8f6b3b157a511e2'", "apiEnabled = $false",
                      "inGameVerified = $false", "capabilities = @('named_options')",
                      "'tests\\test_bridge_addon_build.py'", "'licenses\\OpenMCM-previous-MIT.txt'"):
            self.assertIn(token, script)
        self.assertEqual(script.count("'tools\\check_mcm_bridge_addon.py') $"), 2)
        self.assertNotIn("Remove-Item", script)
        self.assertNotIn("Invoke-WebRequest", script)

    @unittest.skipUnless(POWERSHELL, "PowerShell needed to execute builder guard")
    def test_existing_addon_archive_is_preserved_before_tools_or_generated_writes(self):
        with tempfile.TemporaryDirectory(prefix="bridge-addon-guard-") as temporary:
            root = Path(temporary)
            script = root / "scripts/Build-MCMBridgeAddon.ps1"
            script.parent.mkdir()
            shutil.copyfile(BUILD, script)
            archive = root / "dist/OpenMCM-MCM-Bridge-Addon-0.1.0.zip"
            archive.parent.mkdir()
            original = b"Do not replace a previously built or owner-edited release."
            archive.write_bytes(original)
            result = subprocess.run(
                [POWERSHELL, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                 "-File", str(script)], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Refusing to overwrite an existing MCM Bridge add-on archive",
                          result.stdout + result.stderr)
            self.assertEqual(archive.read_bytes(), original)
            self.assertFalse((root / "build").exists())
            self.assertFalse((root / ".tools").exists())


if __name__ == "__main__":
    unittest.main()
