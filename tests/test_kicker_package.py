"""Structural packaging tests use synthetic PEX envelopes, not the game VM."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from check_kicker import CONTRACTS, RESET_METHOD, validate_package, validate_manager_bytes
from test_contract_checker import _minimal_pex


class KickerPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Scripts').mkdir()
        (self.root / 'Source/Scripts').mkdir(parents=True)
        for contract in CONTRACTS:
            name = contract['script']
            tokens = set(contract['required_identifiers'] + contract['required_exact_identifiers'])
            (self.root / f'Scripts/{name}.pex').write_bytes(
                _minimal_pex(tokens, name, contract['extends']))
            source = ROOT / f'src/compat/jaxonz-kicker/{name}.psc'
            (self.root / f'Source/Scripts/{name}.psc').write_bytes(source.read_bytes())

    def test_exact_component_passes(self):
        report = validate_package(self.root)
        self.assertTrue(report.ok, report.errors)

    def test_original_plugin_is_not_bundled(self):
        (self.root / 'JaxonzMCMKicker.esp').write_bytes(b'not part of patch')
        self.assertFalse(validate_package(self.root).ok)

    def test_missing_source_rejected(self):
        (self.root / 'Source/Scripts/JaxonzMCMKicker.psc').unlink()
        self.assertFalse(validate_package(self.root).ok)

    def test_wrong_parent_rejected(self):
        contract = CONTRACTS[0]
        tokens = set(contract['required_identifiers'] + contract['required_exact_identifiers'])
        (self.root / 'Scripts/JaxonzMCMKicker.pex').write_bytes(
            _minimal_pex(tokens, 'JaxonzMCMKicker', 'Quest'))
        report = validate_package(self.root)
        self.assertTrue(any('KICKER_PEX_PARENT' in error for error in report.errors))

    def test_missing_call_contract_rejected(self):
        contract = CONTRACTS[0]
        tokens = set(contract['required_identifiers'] + contract['required_exact_identifiers']) - {RESET_METHOD}
        (self.root / 'Scripts/JaxonzMCMKicker.pex').write_bytes(
            _minimal_pex(tokens, 'JaxonzMCMKicker', 'ReferenceAlias'))
        self.assertFalse(validate_package(self.root).ok)

    def test_stage_request_not_allowed_as_acknowledgement(self):
        contract = CONTRACTS[0]
        tokens = set(contract['required_identifiers'] + contract['required_exact_identifiers']) | {'SetStage'}
        (self.root / 'Scripts/JaxonzMCMKicker.pex').write_bytes(
            _minimal_pex(tokens, 'JaxonzMCMKicker', 'ReferenceAlias'))
        self.assertFalse(validate_package(self.root).ok)

    def test_manager_requires_compiled_completion_method(self):
        source = (ROOT / 'src/papyrus/SKI_ConfigManager.psc').read_bytes()
        good = _minimal_pex({RESET_METHOD}, 'SKI_ConfigManager', 'SKI_QuestBase')
        result = validate_manager_bytes(good, source)
        self.assertTrue(result.ok, result.errors)
        legacy = _minimal_pex({'ForceReset'}, 'SKI_ConfigManager', 'SKI_QuestBase')
        self.assertFalse(validate_manager_bytes(legacy, source).ok)

    def test_manager_requires_busy_rejection_and_boolean_signature(self):
        source = (ROOT / 'src/papyrus/SKI_ConfigManager.psc').read_bytes()
        pex = _minimal_pex({RESET_METHOD}, 'SKI_ConfigManager', 'SKI_QuestBase')
        legacy = source.replace(b'Bool Function OpenMCM_TryForceReset()', b'Function OpenMCM_TryForceReset()')
        self.assertFalse(validate_manager_bytes(pex, legacy).ok)
        before, busy = source.split(b'State BUSY', 1)
        self.assertFalse(validate_manager_bytes(pex, before + b'State BUSY' + busy.replace(b'Return False', b'Return True')).ok)

    def test_malformed_pex_rejected(self):
        (self.root / 'Scripts/JaxonzMCMKicker.pex').write_bytes(b'not pex')
        self.assertFalse(validate_package(self.root).ok)

    def test_build_compiles_outside_host_and_does_not_copy_original(self):
        build = (ROOT / 'scripts/Build-KickerCompatibility.ps1').read_text()
        self.assertIn("'src\\compat\\jaxonz-kicker'", build)
        self.assertIn("'kicker-compat'", build)
        self.assertIn('--ignorecwd', build)
        self.assertIn('"--import=$source"', build)
        self.assertIn('"--import=$sdk"', build)
        self.assertIn('tools\\sanitize_papyrus_metadata.py', build)
        self.assertIn('tools\\repair_papyrus_identifiers.py', build)
        self.assertIn('tools\\check_kicker.py', build)
        self.assertNotIn('reference-kicker', build)
        self.assertNotIn('SteamLibrary', build)
        fomod = (ROOT / 'scripts/Build-FomodPackage.ps1').read_text()
        self.assertIn('--kicker-data $kickerData', fomod)
        self.assertIn("'jaxonzKicker'", fomod)


if __name__ == '__main__':
    unittest.main()
