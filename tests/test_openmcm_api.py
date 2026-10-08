"""Check opt-in SDK packaging separately from the unchanged SkyUI ABI contract."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT / "tools", ROOT / "tests"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from check_openmcm_api import API_CONTRACTS, validate_package  # noqa: E402
from test_contract_checker import _minimal_pex  # noqa: E402


def api_fixture_payload() -> dict[str, bytes]:
    sources = {
        "OpenMCM": """Scriptname OpenMCM Hidden
Int Function GetAPIVersion() Global
    Return 1
EndFunction
Int Function GetHostAPIVersion() Global
    Return 4
EndFunction
Bool Function HasCapability(String a_capability) Global
    Return False
EndFunction
Bool Function IsAPIEnabled() Global
    Return False
EndFunction
""",
        "OpenMCM_ConfigBase": "Scriptname OpenMCM_ConfigBase extends SKI_ConfigBase Hidden\n"
        + "\n".join(f"Int Function {name}()\n    Return 0\nEndFunction\n"
                    for name in API_CONTRACTS[1]["required_identifiers"]),
    }
    result = {}
    for contract in API_CONTRACTS:
        script = contract["script"]
        symbols = set(contract["required_identifiers"]) | set(contract["required_exact_identifiers"])
        result[f"Scripts/{script}.pex"] = _minimal_pex(symbols, script, contract["extends"])
        result[f"Source/Scripts/{script}.psc"] = sources[script].encode("utf-8")
    return result


class OpenMCMApiPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "Data"
        for relative, raw in api_fixture_payload().items():
            self.write(relative, raw)

    def write(self, relative: str, raw: bytes):
        path = self.data / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def assert_invalid(self, code: str):
        report = validate_package(self.root)
        self.assertFalse(report.ok)
        self.assertTrue(any(code in error for error in report.errors), report.errors)

    def test_accepts_flat_and_wrapped_valid_api(self):
        for target in (self.root, self.data):
            report = validate_package(target)
            self.assertTrue(report.ok, report.errors)

    def test_accepts_zip_without_legacy_mcm_replacement(self):
        archive = self.root / "sdk.zip"
        with zipfile.ZipFile(archive, "w") as output:
            for path in self.data.rglob("*"):
                if path.is_file():
                    output.write(path, path.relative_to(self.root).as_posix())
        report = validate_package(archive)
        self.assertTrue(report.ok, report.errors)

    def test_requires_both_new_compiled_scripts(self):
        for script in ("OpenMCM", "OpenMCM_ConfigBase"):
            path = self.data / f"Scripts/{script}.pex"
            original = path.read_bytes()
            with self.subTest(script=script):
                path.unlink()
                self.assert_invalid("RUNTIME_PATH_MISSING")
                path.write_bytes(original)

    def test_requires_both_new_sources(self):
        for script in ("OpenMCM", "OpenMCM_ConfigBase"):
            path = self.data / f"Source/Scripts/{script}.psc"
            original = path.read_bytes()
            with self.subTest(script=script):
                path.unlink()
                self.assert_invalid("OPENMCM_API_SOURCE_MISSING")
                path.write_bytes(original)

    def test_root_global_script_must_not_extend_quest(self):
        self.write("Scripts/OpenMCM.pex", _minimal_pex({"GetAPIVersion", "GetHostAPIVersion",
                                                      "HasCapability"}, "OpenMCM", "Quest"))
        self.assert_invalid("OPENMCM_API_PEX_PARENT")

    def test_derived_script_parent_must_be_ski_configbase(self):
        self.write("Scripts/OpenMCM_ConfigBase.pex", _minimal_pex({"SKI_ConfigBase"},
                                                                 "OpenMCM_ConfigBase", "Quest"))
        self.assert_invalid("OPENMCM_API_PEX_PARENT")

    def test_rejects_caprica_lowercased_custom_parent(self):
        self.write("Scripts/OpenMCM_ConfigBase.pex", _minimal_pex(set(),
                                                                 "OpenMCM_ConfigBase", "sKI_ConfigBase"))
        self.assert_invalid("PEX_FORBIDDEN_IDENTIFIER")

    def test_global_capability_symbols_are_required(self):
        self.write("Scripts/OpenMCM.pex", _minimal_pex({"GetAPIVersion", "GetHostAPIVersion"},
                                                      "OpenMCM", ""))
        self.assert_invalid("PEX_SYMBOL_MISSING")

    def test_core_named_option_method_is_required(self):
        symbols = set(API_CONTRACTS[1]["required_identifiers"]) - {"SetOptionText"}
        self.write("Scripts/OpenMCM_ConfigBase.pex", _minimal_pex(symbols,
                                                                 "OpenMCM_ConfigBase", "SKI_ConfigBase"))
        self.assert_invalid("PEX_SYMBOL_MISSING")

    def test_source_script_identity_and_parent_are_checked(self):
        self.write("Source/Scripts/OpenMCM_ConfigBase.psc", b"Scriptname OpenMCM_ConfigBase extends Quest\n")
        self.assert_invalid("OPENMCM_API_SOURCE_IDENTITY")

    def test_source_function_names_are_checked_without_comment_false_positive(self):
        path = self.data / "Source/Scripts/OpenMCM.psc"
        path.write_bytes(path.read_bytes().replace(b"Bool Function HasCapability", b"; Bool Function HasCapability"))
        self.assert_invalid("OPENMCM_API_SOURCE_FUNCTION")

    def test_malformed_pex_returns_report(self):
        self.write("Scripts/OpenMCM.pex", b"\xfa\x57\xc0\xdeOpenMCM GetAPIVersion")
        self.assert_invalid("PEX_PARSE_ERROR")


if __name__ == "__main__":
    unittest.main()
