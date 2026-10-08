"""Exercise complete FOMOD ZIP inventories and all real selected-file projections.

Only compiled-runtime validators are mocked: XML parsing, checksums, ZIP safety,
source selection, copy projection, and leakage/version checks execute normally.
Runtime ABI/plugin/PE fixtures have their own dedicated contract test suites.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import itertools
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import check_fomod_package as checker  # noqa: E402
from build_fomod_installer import (  # noqa: E402
    build_installer, MODE_PATHS, NATIVE_PATH, BROWSER_PATH, create_module_config, write_installer_xml,
    FIELD_GUIDE_PATH, FIELD_GUIDE_DOCS,
    KICKER_PATH, KICKER_FILES, KICKER_PLUGIN,
)
from check_mcm_contract import Report  # noqa: E402
from test_openmcm_api import api_fixture_payload  # noqa: E402


VERSION = "1.2.0-alpha.2"
PACKED_VERSION = 0x01020000


class FomodPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        standalone = self.work / "standalone" / "Data"
        skyui = self.work / "skyui" / "Data"
        native = self.work / "native" / "Data"
        shared = {"Interface/quest_journal.swf": b"journal",
                  "Scripts/SKI_ConfigBase.pex": b"config base",
                  "Scripts/SKI_ConfigManager.pex": b"manager",
                  "Scripts/OpenMCM_ConfigMenu.pex": b"status"}
        shared.update(api_fixture_payload())
        self.standalone_payload = dict(shared, **{
            "SkyUI_SE.esp": b"standalone plugin", "Seq/SkyUI_SE.seq": b"standalone seq"})
        self.skyui_payload = dict(shared, **{
            "OpenMCM.esp": b"companion plugin", "Seq/OpenMCM.seq": b"companion seq"})
        self.native_payload = {"SKSE/Plugins/OpenMCMRuntime.dll": b"native",
                               "SKSE/Plugins/OpenMCMRuntime.ini": b"[Patches]\n"}
        for root, payload in ((standalone, self.standalone_payload),
                              (skyui, self.skyui_payload), (native, self.native_payload)):
            for name, contents in payload.items():
                self.put(root, name, contents)
        self.package = self.work / "installer"
        build_installer(standalone, skyui, self.package, VERSION, native)
        for name in ("README.md", "COMPATIBILITY.md", "RELEASE_NOTES.md", "LICENSE",
                     "THIRD_PARTY_NOTICES.md", "docs/OpenMCM-API.md",
                     "examples/OpenMCMExample.psc", "examples/OpenMCMApiExample.psc"):
            self.put(self.package, name, b"release documentation")
        self.put(self.package, "OpenMCM_BUILD.json", json.dumps({
            "version": VERSION, "nativeRuntime": {"pluginVersion": PACKED_VERSION},
            "OpenMCM_API": {"version": 1, "prerelease": True},
        }).encode("utf-8"))
        self.manifest()
        self.projections = []
        self.native_projections = []
        self.standalone_mock = self.patch_validator("validate_standalone", self.capture_standalone)
        self.coexist_mock = self.patch_validator("validate_coexist", self.capture_coexist)
        self.native_mock = self.patch_validator("validate_native", self.capture_native)

    def patch_validator(self, name, capture):
        patcher = mock.patch.object(checker, name, side_effect=capture)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    @staticmethod
    def put(root: Path, name: str, contents: bytes) -> None:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)

    def manifest(self):
        manifest = self.package / "OpenMCM_SHA256SUMS.txt"
        lines = [f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(self.package).as_posix()}"
                 for path in sorted(self.package.rglob("*"))
                 if path.is_file() and path != manifest]
        manifest.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def snapshot(install: Path) -> dict[str, bytes]:
        return {path.relative_to(install / "Data").as_posix(): path.read_bytes()
                for path in (install / "Data").rglob("*") if path.is_file()}

    def capture_standalone(self, install, manifest, profile):
        self.assertEqual(profile, "release")
        self.projections.append(("standalone", self.snapshot(install)))
        return Report(str(install), "release", checks=7)

    def capture_coexist(self, install):
        self.projections.append(("skyui", self.snapshot(install)))
        return Report(str(install), "coexist", checks=9)

    def capture_native(self, install):
        self.native_projections.append(self.snapshot(install))
        return {"plugin_version": PACKED_VERSION}

    def validate(self, target=None) -> Report:
        with contextlib.redirect_stdout(io.StringIO()):
            result = checker.validate_package(target or self.package)
        self.assertIsInstance(result, Report)
        return result

    def assert_error(self, fragment: str):
        result = self.validate()
        self.assertFalse(result.ok)
        self.assertTrue(any(fragment in error for error in result.errors), result.errors)
        return result

    def edit_config(self, mutate):
        path = self.package / "fomod/ModuleConfig.xml"
        xml = ET.parse(path)
        mutate(xml.getroot())
        write_installer_xml(xml, path)
        self.manifest()

    def assert_four_projections(self):
        self.assertEqual(self.standalone_mock.call_count, 2)
        self.assertEqual(self.coexist_mock.call_count, 2)
        self.assertEqual(self.native_mock.call_count, 2)
        self.assertEqual(len(self.projections), 4)
        for mode, base in (("standalone", self.standalone_payload), ("skyui", self.skyui_payload)):
            observed = [payload for name, payload in self.projections if name == mode]
            self.assertIn(base, observed)
            self.assertIn(dict(base, **self.native_payload), observed)
        self.assertTrue(all(not name.startswith("Data/") for _, files in self.projections for name in files))

    def test_directory_projects_all_four_exact_payloads(self):
        result = self.validate()
        self.assertTrue(result.ok, result.errors)
        self.assertGreater(result.checks, 32)
        self.assert_four_projections()

    def enable_complete_source(self):
        # Keep the small pinned dependency fixture active while the FOMOD
        # checker verifies the real nested source ZIP and its manifests.
        from test_full_source_package import FullSourcePackageTests, packager
        fixture = FullSourcePackageTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with contextlib.redirect_stdout(io.StringIO()):
            packager.package(fixture.root, fixture.browser_path, fixture.output, VERSION)
        source = fixture.output.read_bytes()
        self.complete_source_name = f'source/OpenMCM-{VERSION}-Source.zip'
        self.put(self.package, self.complete_source_name, source)
        for name in ('README.txt', 'LICENSE.txt', 'licenses/OpenMCM-previous-MIT.txt'):
            self.put(self.package, name, (fixture.root / name).read_bytes())
        metadata_path = self.package / 'OpenMCM_BUILD.json'
        metadata = json.loads(metadata_path.read_text())
        if 'browserIntegration' in metadata:
            browser_source = fixture.browser_path.read_bytes()
            browser_metadata = metadata['browserIntegration']
            self.put(self.package, browser_metadata['sourceArchive'], browser_source)
            browser_metadata['sourceSha256'] = hashlib.sha256(browser_source).hexdigest().upper()
        metadata['correspondingSource'] = {
            'archive': self.complete_source_name,
            'sha256': hashlib.sha256(source).hexdigest().upper(),
            'scope': 'complete OpenMCM project source plus pinned browser dependencies',
            'license': 'GPL-3.0-or-later for original OpenMCM code; see third-party notices',
        }
        metadata_path.write_text(json.dumps(metadata), encoding='utf-8')
        self.manifest()

    def replace_complete_source(self, raw):
        self.put(self.package, self.complete_source_name, raw)
        path = self.package / 'OpenMCM_BUILD.json'
        metadata = json.loads(path.read_text())
        metadata['correspondingSource']['sha256'] = hashlib.sha256(raw).hexdigest().upper()
        path.write_text(json.dumps(metadata), encoding='utf-8')
        self.manifest()

    def edit_complete_source(self, mutate, *, refresh_inner_manifest=False):
        with zipfile.ZipFile(self.package / self.complete_source_name) as source:
            files = {name: source.read(name) for name in source.namelist()}
        mutate(files)
        if refresh_inner_manifest:
            files['SHA256SUMS.txt'] = ''.join(
                f'{hashlib.sha256(raw).hexdigest()}  {name}\n'
                for name, raw in sorted(files.items()) if name != 'SHA256SUMS.txt'
            ).encode()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as source:
            for name, raw in files.items():
                source.writestr(name, raw)
        self.replace_complete_source(buffer.getvalue())

    def test_complete_source_zip_validates_without_changing_installed_payloads(self):
        self.enable_complete_source()
        archive = self.work / 'with-complete-source.zip'
        with zipfile.ZipFile(archive, 'w') as package:
            for path in self.package.rglob('*'):
                if path.is_file():
                    package.write(path, path.relative_to(self.package).as_posix())
        result = self.validate(archive)
        self.assertTrue(result.ok, result.errors)
        self.assert_four_projections()

    def test_complete_source_metadata_hash_is_checked_independently_of_outer_manifest(self):
        self.enable_complete_source()
        path = self.package / 'OpenMCM_BUILD.json'
        metadata = json.loads(path.read_text())
        metadata['correspondingSource']['sha256'] = '0' * 64
        path.write_text(json.dumps(metadata), encoding='utf-8')
        self.manifest()
        self.assert_error('Complete corresponding source checksum mismatch')
        self.assertFalse(self.projections)

    def test_complete_source_metadata_requires_archive(self):
        self.enable_complete_source()
        (self.package / self.complete_source_name).unlink()
        self.manifest()
        self.assert_error('Missing complete corresponding source archive')
        self.assertFalse(self.projections)

    def test_complete_source_metadata_requires_plain_text_notices(self):
        self.enable_complete_source()
        for name in ('README.txt', 'LICENSE.txt', 'licenses/OpenMCM-previous-MIT.txt'):
            path = self.package / name
            raw = path.read_bytes()
            with self.subTest(name=name):
                path.unlink()
                self.manifest()
                self.assert_error('Missing corresponding source notice: ' + name)
                self.assertFalse(self.projections)
                path.write_bytes(raw)

    def test_complete_source_metadata_must_describe_scope_and_license(self):
        self.enable_complete_source()
        path = self.package / 'OpenMCM_BUILD.json'
        original = json.loads(path.read_text())
        for key in ('scope', 'license'):
            metadata = json.loads(json.dumps(original))
            metadata['correspondingSource'][key] = 'incorrect'
            with self.subTest(key=key):
                path.write_text(json.dumps(metadata), encoding='utf-8')
                self.manifest()
                self.assert_error('Corresponding source metadata mismatch: ' + key)
                self.assertFalse(self.projections)

    def test_complete_source_metadata_rejects_invalid_shapes_and_paths(self):
        self.enable_complete_source()
        path = self.package / 'OpenMCM_BUILD.json'
        original = json.loads(path.read_text())
        for value in (None, [], '../source.zip', {'archive': '../source.zip'},
                      {'archive': 'source/../source.zip'}, {'archive': 'source\\source.zip'}):
            metadata = json.loads(json.dumps(original))
            metadata['correspondingSource'] = value
            with self.subTest(value=value):
                path.write_text(json.dumps(metadata), encoding='utf-8')
                self.manifest()
                self.assert_error('Corresponding source')
                self.assertFalse(self.projections)

    def test_complete_source_inner_hash_is_checked_after_outer_hashes_are_updated(self):
        self.enable_complete_source()
        self.edit_complete_source(lambda files: files.update({'README.md': b'altered source notice'}))
        self.assert_error('Corresponding source:')
        self.assertFalse(self.projections)

    def test_complete_source_key_file_and_notice_are_required_inside_archive(self):
        self.enable_complete_source()
        original = (self.package / self.complete_source_name).read_bytes()
        for name in ('src/actionscript/ConfigPanel.as', 'LICENSE.txt',
                     'licenses/OpenMCM-previous-MIT.txt'):
            with self.subTest(name=name):
                self.replace_complete_source(original)
                self.edit_complete_source(lambda files: files.pop(name), refresh_inner_manifest=True)
                self.assert_error('Corresponding source:')
                self.assertFalse(self.projections)

    def test_complete_source_unsafe_inventory_is_rejected_after_hashes_are_updated(self):
        self.enable_complete_source()
        self.edit_complete_source(lambda files: files.update({'../outside.py': b'unsafe'}),
                                  refresh_inner_manifest=True)
        self.assert_error('Corresponding source:')
        self.assertFalse(self.projections)

    def test_complete_source_malformed_archive_is_reported_without_projection(self):
        self.enable_complete_source()
        self.replace_complete_source(b'not a source ZIP')
        self.assert_error('Corresponding source:')
        self.assertFalse(self.projections)

    def test_complete_source_version_must_match_release_metadata(self):
        self.enable_complete_source()
        def change_version(files):
            metadata = json.loads(files['OPENMCM-SOURCE.json'])
            metadata['version'] = '9.0.0'
            files['OPENMCM-SOURCE.json'] = json.dumps(metadata).encode()
        self.edit_complete_source(change_version, refresh_inner_manifest=True)
        self.assert_error('Corresponding source:')
        self.assertFalse(self.projections)

    def test_complete_source_browser_provenance_must_match_separate_browser_source(self):
        self.enable_browser()
        self.enable_complete_source()
        result = self.validate()
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(len(self.projections), 8)
        self.projections.clear()
        def change_browser_digest(files):
            metadata = json.loads(files['OPENMCM-SOURCE.json'])
            metadata['browser_source_sha256'] = '0' * 64
            files['OPENMCM-SOURCE.json'] = json.dumps(metadata).encode()
        self.edit_complete_source(change_browser_digest, refresh_inner_manifest=True)
        self.assert_error('Corresponding source:')
        self.assertFalse(self.projections)

    def enable_browser(self):
        from test_browser_native import browser_fixture
        dll = bytes(browser_fixture())
        source = b'corresponding source fixture'
        self.put(self.package, BROWSER_PATH + '/SKSE/Plugins/OpenMCMBrowser.dll', dll)
        self.put(self.package, 'docs/OpenMCM-Browser.md', b'browser guide')
        self.put(self.package, 'LICENSE-OpenMCMBrowser-GPL-3.0.txt', b'licence fixture')
        self.put(self.package, 'source/browser.zip', source)
        metadata_path = self.package / 'OpenMCM_BUILD.json'
        metadata = json.loads(metadata_path.read_text())
        metadata['browserIntegration'] = {
            'registryLimit': 128, 'sourceArchive': 'source/browser.zip',
            'sourceSha256': hashlib.sha256(source).hexdigest().upper(),
            'dllSha256': hashlib.sha256(dll).hexdigest().upper(),
        }
        metadata_path.write_text(json.dumps(metadata), encoding='utf-8')
        write_installer_xml(create_module_config(VERSION, include_native=True, include_browser=True),
                            self.package / 'fomod/ModuleConfig.xml')
        self.manifest()

    def test_browser_projects_eight_disjoint_combinations(self):
        self.enable_browser()
        result = self.validate()
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(len(self.projections), 8)
        self.assertEqual(self.native_mock.call_count, 4)
        browser_path = 'SKSE/Plugins/OpenMCMBrowser.dll'
        for mode in ('standalone', 'skyui'):
            selections = [payload for name, payload in self.projections if name == mode]
            pairs = {(browser_path in files, 'SKSE/Plugins/OpenMCMRuntime.dll' in files) for files in selections}
            self.assertEqual(pairs, {(False, False), (False, True), (True, False), (True, True)})

    def enable_guide(self):
        # Genuine tiny ESP/VMAD/SEQ/PEX structures, not mocked guide validation.
        from test_field_guide_package import FieldGuidePackageTests
        fixture = FieldGuidePackageTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.assertTrue(fixture.report().ok)
        self.guide_payload = {}
        for path in fixture.root.rglob('*'):
            if not path.is_file():
                continue
            relative = path.relative_to(fixture.root).as_posix()
            raw = path.read_bytes()
            if relative.casefold().startswith('data/'):
                self.guide_payload[relative[5:]] = raw
                target = FIELD_GUIDE_PATH + '/' + relative[5:]
            else:
                target = FIELD_GUIDE_DOCS + '/' + relative
            self.put(self.package, target, raw)
        metadata_path = self.package / 'OpenMCM_BUILD.json'
        metadata = json.loads(metadata_path.read_text())
        metadata['fieldGuide'] = {
            'version': '1.0.0', 'installedByDefault': False,
            'dataPath': FIELD_GUIDE_PATH, 'authorFilesPath': FIELD_GUIDE_DOCS,
        }
        metadata_path.write_text(json.dumps(metadata), encoding='utf-8')
        write_installer_xml(create_module_config(VERSION, include_native=True,
                            include_browser='browserIntegration' in metadata, include_field_guide=True),
                            self.package / 'fomod/ModuleConfig.xml')
        self.manifest()

    def test_guide_and_browser_project_all_sixteen_combinations(self):
        self.enable_browser()
        self.enable_guide()
        result = self.validate()
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(len(self.projections), 16)
        self.assertEqual(self.native_mock.call_count, 8)
        # Host validators keep the strict host-only ABI; guide presence is
        # observed independently in the complete native-enabled projections.
        for _, payload in self.projections:
            self.assertFalse(any('fieldguide' in name.casefold() for name in payload))
        guide_keys = {name.casefold() for name in self.guide_payload}
        selected = []
        for payload in self.native_projections:
            guide = {name.casefold(): raw for name, raw in payload.items()
                     if name.casefold() in guide_keys}
            self.assertIn(guide, ({}, {name.casefold(): raw for name, raw in self.guide_payload.items()}))
            selected.append(bool(guide))
        self.assertEqual(selected.count(True), 4)
        self.assertEqual(selected.count(False), 4)

    def enable_kicker(self):
        # Compiled script validation is exercised by the dedicated Kicker suite;
        # this fixture checks the installer inventories and projected bytes.
        self.kicker_payload = {name: ("kicker fixture: " + name).encode() for name in KICKER_FILES}
        for name, raw in self.kicker_payload.items():
            self.put(self.package, KICKER_PATH + '/' + name, raw)
        self.put(self.package, 'docs/Jaxonz-MCM-Kicker.md', b'kicker guide')
        metadata_path = self.package / 'OpenMCM_BUILD.json'
        metadata = json.loads(metadata_path.read_text())
        metadata['jaxonzKicker'] = {
            'version': '1.0.1', 'installedByDefault': False,
            'dataPath': KICKER_PATH, 'requiresPlugin': KICKER_PLUGIN,
            'detectionRecommended': True,
            'requiresManagerMethod': 'OpenMCM_TryForceReset',
        }
        metadata_path.write_text(json.dumps(metadata), encoding='utf-8')
        write_installer_xml(create_module_config(VERSION, include_native=True,
                            include_browser='browserIntegration' in metadata,
                            include_field_guide='fieldGuide' in metadata, include_kicker=True),
                            self.package / 'fomod/ModuleConfig.xml')
        patcher = mock.patch('check_kicker.validate_package',
                             return_value=Report('kicker fixture', 'kicker', checks=5))
        self.kicker_mock = patcher.start()
        self.addCleanup(patcher.stop)
        host_patcher = mock.patch('check_kicker.validate_manager_bytes',
                                  return_value=Report('host fixture', 'kicker-host', checks=5))
        self.kicker_host_mock = host_patcher.start()
        self.addCleanup(host_patcher.stop)
        self.manifest()

    def test_kicker_requires_matching_manager_in_both_modes(self):
        self.enable_kicker()
        self.kicker_host_mock.side_effect = [Report('standalone', 'kicker-host'),
            Report('old skyui host', 'kicker-host', errors=['no completion method'])]
        self.assert_error('Kicker skyui host: no completion method')
        self.assertFalse(self.projections)

    def test_kicker_browser_and_guide_project_all_32_combinations(self):
        self.enable_browser()
        self.enable_guide()
        self.enable_kicker()
        result = self.validate()
        self.assertTrue(result.ok, result.errors)
        self.kicker_mock.assert_called_once()
        self.assertEqual(len(self.projections), 32)
        self.assertEqual(self.native_mock.call_count, 16)
        for _, payload in self.projections:
            self.assertFalse(KICKER_FILES.intersection(name.casefold() for name in payload))
            self.assertFalse(any('fieldguide' in name.casefold() for name in payload))
        for mode, marker in (('standalone', 'SkyUI_SE.esp'), ('skyui', 'OpenMCM.esp')):
            selections = [payload for payload in self.native_projections if marker in payload]
            combinations = set()
            for payload in selections:
                selected = {name.casefold(): raw for name, raw in payload.items()
                            if name.casefold() in KICKER_FILES}
                self.assertIn(selected, ({}, self.kicker_payload))
                combinations.add((bool(selected), 'OpenMCM_FieldGuide.esp' in payload,
                                  'SKSE/Plugins/OpenMCMBrowser.dll' in payload))
            self.assertEqual(combinations, set(itertools.product((False, True), repeat=3)), mode)

    def test_kicker_zip_preserves_exact_script_payload(self):
        self.enable_kicker()
        archive = self.work / 'kicker.zip'
        with zipfile.ZipFile(archive, 'w') as package:
            for path in self.package.rglob('*'):
                if path.is_file():
                    package.write(path, path.relative_to(self.package).as_posix())
        result = self.validate(archive)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(len(self.projections), 8)
        self.kicker_mock.assert_called_once()

    def test_kicker_requires_metadata_and_installer_choice(self):
        self.put(self.package, KICKER_PATH + '/Scripts/JaxonzMCMKicker.pex', b'untracked kicker')
        self.manifest()
        self.assert_error('Kicker files require build metadata')
        self.assertFalse(self.projections)

    def test_kicker_original_plugin_and_archive_cannot_be_bundled(self):
        self.enable_kicker()
        for name in ('JaxonzMCMKicker.esp', 'JaxonzMCMKicker.bsa'):
            with self.subTest(name=name):
                self.put(self.package, 'extras/' + name, b'original mod')
                self.manifest()
                self.assert_error('Original Jaxonz MCM Kicker plugin/archive must not be bundled')
                self.assertFalse(self.projections)
                (self.package / 'extras' / name).unlink()

    def test_kicker_requires_exact_four_files_even_when_validator_is_mocked(self):
        self.enable_kicker()
        missing = self.package / KICKER_PATH / 'source/scripts/jaxonzmcmkicker.psc'
        missing.unlink()
        self.manifest()
        self.assert_error('Kicker component must contain exactly two PEX and two source scripts')
        self.assertFalse(self.projections)

    def test_kicker_cannot_leak_into_host_mode_when_omitted(self):
        self.enable_kicker()
        self.put(self.package, MODE_PATHS['standalone'] + '/Scripts/JaxonzMCMKicker.pex', b'leaked')
        self.manifest()
        self.assert_error('Kicker payload outside optional component')
        self.assertFalse(self.projections)

    def test_kicker_requires_documentation(self):
        self.enable_kicker()
        (self.package / 'docs/Jaxonz-MCM-Kicker.md').unlink()
        self.manifest()
        self.assert_error('Missing Jaxonz MCM Kicker guide')
        self.assertFalse(self.projections)

    def test_kicker_metadata_preserves_external_requirement_and_optional_layout(self):
        self.enable_kicker()
        path = self.package / 'OpenMCM_BUILD.json'
        metadata = json.loads(path.read_text())
        original = dict(metadata['jaxonzKicker'])
        for key, wrong in (('version', '2.0.0'), ('installedByDefault', True),
                            ('dataPath', 'Data'), ('requiresPlugin', 'SkyUI_SE.esp'),
                            ('requiresManagerMethod', 'ForceReset')):
            with self.subTest(key=key):
                metadata['jaxonzKicker'] = dict(original, **{key: wrong})
                path.write_text(json.dumps(metadata), encoding='utf-8')
                self.manifest()
                self.assert_error('Jaxonz MCM Kicker metadata mismatch: ' + key)
                self.assertFalse(self.projections)

    def test_kicker_script_contract_failure_blocks_projection(self):
        self.enable_kicker()
        self.kicker_mock.return_value = Report('kicker fixture', 'kicker', checks=1,
                                               errors=['invalid refresh contract'])
        self.assert_error('Jaxonz MCM Kicker component: invalid refresh contract')
        self.assertFalse(self.projections)

    def test_kicker_xml_cannot_bypass_original_plugin_detection(self):
        self.enable_kicker()
        def mutation(root):
            options = root.findall('./installSteps/installStep/optionalFileGroups/group')[-1]
            dependency = options.find('./plugins/plugin/typeDescriptor/dependencyType/patterns/pattern/dependencies')
            dependency.find('fileDependency').set('file', 'SkyUI_SE.esp')
        self.edit_config(mutation)
        self.assert_error('Installer differs')
        self.assertFalse(self.projections)

    def test_guide_zip_reconstructs_source_manifest_and_payload(self):
        self.enable_browser()
        self.enable_guide()
        archive = self.work / 'full.zip'
        with zipfile.ZipFile(archive, 'w') as package:
            for path in self.package.rglob('*'):
                if path.is_file():
                    package.write(path, path.relative_to(self.package).as_posix())
        result = self.validate(archive)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(len(self.projections), 16)

    def test_guide_modified_bytes_fail_own_manifest_despite_outer_checksum(self):
        self.enable_guide()
        self.put(self.package, FIELD_GUIDE_DOCS + '/README.md', b'changed')
        self.manifest()
        self.assert_error('Field Guide component: CHECKSUM_MISMATCH')
        self.assertFalse(self.projections)

    def test_guide_source_file_cannot_smuggle_extra_native_payload(self):
        self.enable_guide()
        self.put(self.package, FIELD_GUIDE_DOCS + '/Source/other.dll', b'MZ')
        self.manifest()
        self.assert_error('GUIDE_ROOT_PAYLOAD')

    def test_guide_missing_component_or_source_rejected(self):
        self.enable_guide()
        (self.package / FIELD_GUIDE_PATH / 'OpenMCM_FieldGuide.esp').unlink()
        self.manifest()
        self.assert_error('GUIDE_REQUIRED')
        self.assertFalse(self.projections)

    def test_guide_cannot_leak_into_host_mode_when_omitted(self):
        self.enable_guide()
        self.put(self.package, MODE_PATHS['standalone'] + '/OpenMCM_FieldGuide.esp',
                 self.guide_payload['OpenMCM_FieldGuide.esp'])
        self.manifest()
        self.assert_error('Field Guide payload differs from selected optional component')

    def test_guide_requires_explicit_metadata(self):
        self.put(self.package, FIELD_GUIDE_DOCS + '/README.md', b'untracked guide')
        self.manifest()
        self.assert_error('Field Guide files require build metadata')

    def test_guide_metadata_must_preserve_opt_in_and_layout(self):
        self.enable_guide()
        metadata_path = self.package / 'OpenMCM_BUILD.json'
        metadata = json.loads(metadata_path.read_text())
        metadata['fieldGuide']['installedByDefault'] = True
        metadata_path.write_text(json.dumps(metadata), encoding='utf-8')
        self.manifest()
        self.assert_error('Field Guide metadata mismatch: installedByDefault')

    def test_browser_source_is_required_even_if_dll_is_optional(self):
        self.enable_browser()
        (self.package / 'source/browser.zip').unlink()
        self.manifest()
        self.assert_error('Missing browser source/licence/guide')
        self.assertFalse(self.projections)

    def test_browser_corresponding_source_hash_is_checked(self):
        self.enable_browser()
        self.put(self.package, 'source/browser.zip', b'different source')
        self.manifest()
        self.assert_error('Browser corresponding source checksum mismatch')

    def test_browser_binary_hash_is_bound_to_metadata(self):
        self.enable_browser()
        binary = self.package / BROWSER_PATH / 'SKSE/Plugins/OpenMCMBrowser.dll'
        binary.write_bytes(binary.read_bytes() + b'different but still valid PE overlay')
        self.manifest()
        self.assert_error('browser DLL checksum mismatch')

    def test_zip_projects_all_four_exact_payloads(self):
        archive = self.work / "release.zip"
        with zipfile.ZipFile(archive, "w") as package:
            for path in self.package.rglob("*"):
                if path.is_file():
                    package.write(path, path.relative_to(self.package).as_posix())
        result = self.validate(archive)
        self.assertTrue(result.ok, result.errors)
        self.assert_four_projections()

    def test_corrupt_payload_hash_blocks_projection(self):
        self.put(self.package, MODE_PATHS["skyui"] + "/Interface/quest_journal.swf", b"tampered")
        self.assert_error("CHECKSUM_MISMATCH")
        self.assertFalse(self.projections)

    def test_single_quoted_xml_header_rejected_even_when_well_formed_and_checksummed(self):
        for relative in ("fomod/ModuleConfig.xml", "fomod/info.xml"):
            path = self.package / relative
            original = path.read_bytes()
            with self.subTest(relative=relative):
                # This is the exact ElementTree default used in alpha.2.
                ET.parse(path).write(path, encoding="utf-8", xml_declaration=True)
                ET.parse(path)  # Legal XML, but not accepted by Nexus StringStream.
                self.manifest()
                self.assert_error("Vortex-compatible double-quoted UTF-8 declaration")
                self.assertFalse(self.projections)
                path.write_bytes(original)

    def test_canonical_declarations_also_accept_crlf(self):
        for relative in ("fomod/ModuleConfig.xml", "fomod/info.xml"):
            path = self.package / relative
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.manifest()
        result = self.validate()
        self.assertTrue(result.ok, result.errors)
        self.assert_four_projections()

    def test_unlisted_file_blocks_projection(self):
        self.put(self.package, "unexpected.txt", b"not listed")
        self.assert_error("CHECKSUM_FILE_UNLISTED")
        self.assertFalse(self.projections)

    def test_missing_manifest_blocks_projection(self):
        (self.package / "OpenMCM_SHA256SUMS.txt").unlink()
        self.assert_error("CHECKSUM_MANIFEST_MISSING")
        self.assertFalse(self.projections)

    def test_unconditional_data_rejected_even_when_checksummed(self):
        self.put(self.package, "Data/SkyUI_SE.esp", b"bypasses mode choice")
        self.manifest()
        self.assert_error("Unconditional Data")
        self.assertFalse(self.projections)

    def test_diagnostic_executable_rejected_even_when_checksummed(self):
        self.put(self.package, "diagnostics/test.exe", b"not a release artifact")
        self.manifest()
        self.assert_error("Build/diagnostic")

    def test_destination_cannot_add_nested_data_directory(self):
        self.edit_config(lambda root: root.find(".//files/folder").set("destination", "Data"))
        self.assert_error("Installer differs")
        self.assertFalse(self.projections)

    def test_coexist_option_cannot_install_standalone_branch(self):
        def mutation(root):
            root.findall(".//files/folder")[1].set("source", MODE_PATHS["standalone"])
        self.edit_config(mutation)
        self.assert_error("Installer differs")
        self.assertFalse(self.projections)

    def test_source_traversal_is_rejected_before_copy(self):
        self.edit_config(lambda root: root.find(".//files/folder").set("source", "../outside"))
        self.assert_error("Installer differs")
        self.assertFalse(self.projections)

    def test_weakened_skyui_detection_is_rejected(self):
        def mutation(root):
            for condition in root.findall(".//pattern/dependencies"):
                # Turn plugin AND real markers into plugin OR markers.
                condition.set("operator", "Or")
        self.edit_config(mutation)
        self.assert_error("Installer differs")
        self.assertFalse(self.projections)

    def test_added_unconditional_installer_files_are_rejected(self):
        def mutation(root):
            required = ET.SubElement(root, "requiredInstallFiles")
            ET.SubElement(required, "folder", source=MODE_PATHS["standalone"], destination="")
        self.edit_config(mutation)
        self.assert_error("Installer differs")
        self.assertFalse(self.projections)

    def test_metadata_version_mismatch_is_reported(self):
        path = self.package / "fomod/info.xml"
        xml = ET.parse(path)
        xml.find("Version").text = "1.1.0"
        write_installer_xml(xml, path)
        self.manifest()
        self.assert_error("version mismatch")

    def test_native_binary_version_mismatch_is_reported(self):
        self.native_mock.side_effect = lambda _: {"plugin_version": 0x01010000}
        self.assert_error("incorrect native plugin version")

    def test_native_build_metadata_version_mismatch_is_reported(self):
        self.put(self.package, "OpenMCM_BUILD.json", json.dumps({
            "version": VERSION, "nativeRuntime": {"pluginVersion": 0x01010000},
            "OpenMCM_API": {"version": 1, "prerelease": True},
        }).encode("utf-8"))
        self.manifest()
        self.assert_error("Build metadata native version mismatch")

    def test_omitted_native_component_must_not_leak_from_mode(self):
        self.put(self.package, MODE_PATHS["standalone"] + "/SKSE/Plugins/OpenMCMRuntime.ini", b"leaked")
        self.manifest()
        self.assert_error("omitted native component leaked files")

    def test_runtime_contract_errors_remain_in_report_with_mode_context(self):
        self.coexist_mock.side_effect = lambda root: Report(str(root), "coexist", checks=3,
                                                          errors=["synthetic broken companion"])
        result = self.assert_error("synthetic broken companion")
        self.assertTrue(any("With SkyUI" in error for error in result.errors))

    def test_missing_coexist_plugin_cannot_reroute_validation_to_standalone(self):
        (self.package / MODE_PATHS["skyui"] / "OpenMCM.esp").unlink()
        self.manifest()
        # Mocks accept bytes deliberately: dispatch must follow the selected
        # installer mode, never the presence/absence of an untrusted payload file.
        result = self.validate()
        self.assertLessEqual(self.standalone_mock.call_count, 2)
        self.assertTrue(not result.ok or self.coexist_mock.call_count >= 1)

    def test_standalone_mode_requires_opt_in_api_in_each_projection(self):
        (self.package / MODE_PATHS["standalone"] / "Scripts/OpenMCM.pex").unlink()
        self.manifest()
        self.assert_error("Scripts/OpenMCM.pex")

    def test_api_documentation_and_example_are_required(self):
        for relative in ("docs/OpenMCM-API.md", "examples/OpenMCMApiExample.psc"):
            path = self.package / relative
            raw = path.read_bytes()
            with self.subTest(relative=relative):
                path.unlink()
                self.manifest()
                self.assert_error("Missing installer file: " + relative)
                path.write_bytes(raw)

    def test_api_metadata_must_identify_prerelease_v1(self):
        path = self.package / "OpenMCM_BUILD.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        metadata["OpenMCM_API"]["prerelease"] = False
        path.write_text(json.dumps(metadata), encoding="utf-8")
        self.manifest()
        self.assert_error("OpenMCM_API version 1 as prerelease")

    def test_malformed_xml_cli_returns_failure_without_projection(self):
        self.put(self.package, "fomod/ModuleConfig.xml", b"<config>")
        self.manifest()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(checker.main([str(self.package)]), 1)
        self.assertFalse(self.projections)


if __name__ == "__main__":
    unittest.main()
