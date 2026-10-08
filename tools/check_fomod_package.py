#!/usr/bin/env python3
"""Validate the complete ZIP and each possible FOMOD selected-install tree.

Projection is into temporary directories only. No installed game is read or
modified; successful checks do not establish live SkyUI/MCM compatibility.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path, PurePosixPath
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

from build_fomod_installer import (XML_DECLARATION, create_module_config,
                                   FIELD_GUIDE_PATH, FIELD_GUIDE_DOCS,
                                   KICKER_PATH, KICKER_PLUGIN, KICKER_FILES, MODE_PATHS)
from check_field_guide import DATA_FILES as GUIDE_DATA_FILES, validate_package as validate_field_guide
from check_mcm_contract import (PackageView, Report, _validate_checksum_manifest,
                                default_manifest, validate as validate_standalone)
from check_native_runtime import validate as validate_native
from check_skyui_coexist import validate_package as validate_coexist
from check_openmcm_api import validate_package as validate_api

GUIDE_DATA_RELATIVE = frozenset(name[5:] for name in GUIDE_DATA_FILES)


def validate_corresponding_source(view: PackageView, build: dict, report: Report) -> None:
    """Verify complete source for new releases without changing old packages."""
    if 'correspondingSource' not in build:
        return
    metadata = build['correspondingSource']
    report.check(isinstance(metadata, dict), 'Corresponding source metadata must be an object')
    if not isinstance(metadata, dict):
        return
    for name in ('README.txt', 'LICENSE.txt', 'licenses/OpenMCM-previous-MIT.txt',
                 'THIRD_PARTY_NOTICES.md'):
        report.check(view.get(name) is not None, f'Missing corresponding source notice: {name}')
    for key, expected in (
        ('scope', 'complete OpenMCM project source plus pinned browser dependencies'),
        ('license', 'GPL-3.0-or-later for original OpenMCM code; see third-party notices'),
    ):
        report.check(metadata.get(key) == expected, f'Corresponding source metadata mismatch: {key}')
    archive = metadata.get('archive')
    safe_archive = (isinstance(archive, str) and '\\' not in archive and
                    len(archive.split('/')) == 2 and archive.startswith('source/') and
                    archive.endswith('.zip') and
                    all(part not in ('', '.', '..') and ':' not in part and '\0' not in part
                        for part in archive.split('/')))
    report.check(safe_archive, 'Corresponding source archive must be a safe source/*.zip path')
    if not safe_archive:
        return
    entry = view.get(archive)
    report.check(entry is not None, f'Missing complete corresponding source archive: {archive}')
    if entry is None:
        return
    raw = view.read_bytes(entry)
    digest = metadata.get('sha256')
    report.check(isinstance(digest, str) and hashlib.sha256(raw).hexdigest() == digest.lower(),
                 'Complete corresponding source checksum mismatch')
    from package_openmcm_source import validate_source_archive
    try:
        browser_metadata = build.get('browserIntegration', {})
        validate_source_archive(raw, version=build.get('version'), browser_sha256=(
            browser_metadata.get('sourceSha256') if isinstance(browser_metadata, dict) else None))
    except (ValueError, zipfile.BadZipFile) as error:
        report.check(False, f'Corresponding source: {error}')
    else:
        report.check(True, 'Complete corresponding source inventory and manifest verified')


def xml_shape(node: ET.Element):
    return (node.tag, sorted(node.attrib.items()), (node.text or '').strip(),
            [xml_shape(child) for child in node])


def validate_guide_component(view: PackageView, build: dict, report: Report) -> dict[str, bytes]:
    """Reconstitute the untouched sample package and verify its own manifest.

    The four installable files are split from author material by the installer.
    Reconstruction checks actual ESP/VMAD/PEX/SEQ bytes, not only selection XML.
    Returned keys are Data-relative for checking every selected installation.
    """
    enabled = 'fieldGuide' in build
    prefixes = (FIELD_GUIDE_PATH.casefold() + '/', FIELD_GUIDE_DOCS.casefold() + '/')
    entries = [entry for entry in view.entries if entry.key.startswith(prefixes)]
    if not enabled:
        report.check(not entries, 'Field Guide files require build metadata and an installer choice')
        return {}
    metadata = build['fieldGuide']
    report.check(isinstance(metadata, dict), 'Field Guide metadata must be an object')
    if not isinstance(metadata, dict):
        return {}
    for key, expected in (('version', '1.0.0'), ('installedByDefault', False),
                          ('dataPath', FIELD_GUIDE_PATH), ('authorFilesPath', FIELD_GUIDE_DOCS)):
        report.check(metadata.get(key) == expected, f'Field Guide metadata mismatch: {key}')
    payload = {}
    with tempfile.TemporaryDirectory(prefix='openmcm-guide-verify-') as temporary:
        root = Path(temporary)
        reconstructed = set()
        for entry in entries:
            is_data = entry.key.startswith(prefixes[0])
            prefix = prefixes[0] if is_data else prefixes[1]
            relative = ('Data/' if is_data else '') + entry.name[len(prefix):]
            parts = PurePosixPath(relative).parts
            if not parts or any(part in ('', '.', '..') or ':' in part for part in parts):
                report.check(False, f'Unsafe Field Guide path: {entry.name}')
                continue
            key = relative.casefold()
            if key in reconstructed:
                report.check(False, f'Duplicate reconstructed Field Guide path: {relative}')
                continue
            reconstructed.add(key)
            raw = view.read_bytes(entry)
            destination = root.joinpath(*parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            if is_data:
                payload[key[5:]] = raw
        result = validate_field_guide(root)
        report.checks += result.checks
        report.errors.extend(f'Field Guide component: {error}' for error in result.errors)
    return payload


def validate_kicker_component(view: PackageView, build: dict, report: Report) -> dict[str, bytes]:
    """Check the optional script replacement once before projecting selections."""
    prefix = KICKER_PATH.casefold() + '/'
    entries = [entry for entry in view.entries if entry.key.startswith(prefix)]
    for entry in view.entries:
        basename = PurePosixPath(entry.key).name
        report.check(basename not in ('jaxonzmcmkicker.esp', 'jaxonzmcmkicker.bsa'),
                     f'Original Jaxonz MCM Kicker plugin/archive must not be bundled: {entry.name}')
        if basename in {PurePosixPath(name).name for name in KICKER_FILES}:
            report.check(entry.key.startswith(prefix),
                         f'Jaxonz MCM Kicker payload outside optional component: {entry.name}')
    if 'jaxonzKicker' not in build:
        report.check(not entries, 'Jaxonz MCM Kicker files require build metadata and an installer choice')
        return {}
    metadata = build['jaxonzKicker']
    report.check(isinstance(metadata, dict), 'Jaxonz MCM Kicker metadata must be an object')
    if not isinstance(metadata, dict):
        return {}
    for key, expected in (('version', '1.0.1'), ('installedByDefault', False),
                          ('dataPath', KICKER_PATH), ('requiresPlugin', KICKER_PLUGIN),
                          ('requiresManagerMethod', 'OpenMCM_TryForceReset')):
        report.check(metadata.get(key) == expected, f'Jaxonz MCM Kicker metadata mismatch: {key}')
    report.check(view.get('docs/Jaxonz-MCM-Kicker.md') is not None,
                 'Missing Jaxonz MCM Kicker guide: docs/Jaxonz-MCM-Kicker.md')
    from check_kicker import validate_manager_bytes
    for mode, host_prefix in MODE_PATHS.items():
        manager = view.get(host_prefix + '/Scripts/SKI_ConfigManager.pex')
        source = view.get(host_prefix + '/Source/Scripts/SKI_ConfigManager.psc')
        result = validate_manager_bytes(view.read_bytes(manager) if manager else b'',
                                        view.read_bytes(source) if source else b'')
        report.checks += result.checks
        report.errors.extend(f'Kicker {mode} host: {error}' for error in result.errors)
    payload = {}
    with tempfile.TemporaryDirectory(prefix='openmcm-kicker-verify-') as temporary:
        data = Path(temporary) / 'Data'
        data.mkdir()
        for entry in entries:
            relative = entry.name[len(prefix):]
            parts = PurePosixPath(relative).parts
            if not parts or any(part in ('', '.', '..') or ':' in part for part in parts):
                report.check(False, f'Unsafe Jaxonz MCM Kicker path: {entry.name}')
                continue
            raw = view.read_bytes(entry)
            destination = data.joinpath(*parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            payload[relative.casefold()] = raw
        report.check(set(payload) == KICKER_FILES,
                     'Jaxonz MCM Kicker component must contain exactly two PEX and two source scripts')
        from check_kicker import validate_package as validate_kicker
        result = validate_kicker(data)
        report.checks += result.checks
        report.errors.extend(f'Jaxonz MCM Kicker component: {error}' for error in result.errors)
    return payload


def validate_package(target: Path) -> Report:
    report = Report(str(target.resolve()), 'fomod')
    with PackageView(target) as view:
        _validate_checksum_manifest(view, report, required=True)
        required = ('fomod/ModuleConfig.xml', 'fomod/info.xml', 'OpenMCM_BUILD.json',
                    'README.md', 'COMPATIBILITY.md', 'RELEASE_NOTES.md',
                    'LICENSE', 'THIRD_PARTY_NOTICES.md', 'docs/OpenMCM-API.md',
                    'examples/OpenMCMExample.psc', 'examples/OpenMCMApiExample.psc')
        for name in required:
            report.check(view.get(name) is not None, f'Missing installer file: {name}')
        if not report.ok:
            return report
        build = json.loads(view.read_text(view.get('OpenMCM_BUILD.json')))
        version = build['version']
        validate_corresponding_source(view, build, report)
        api = build.get('OpenMCM_API', {})
        report.check(api.get('version') == 1 and api.get('prerelease') is True,
                     'Build metadata must declare opt-in OpenMCM_API version 1 as prerelease')
        xml_documents = {}
        for name in ('fomod/ModuleConfig.xml', 'fomod/info.xml'):
            raw = view.read_bytes(view.get(name))
            # Parsing alone discards the declaration and misses Vortex's
            # quote-sensitive UTF-16 StringStream conversion failure.
            report.check(raw.startswith(XML_DECLARATION + b'\n') or
                         raw.startswith(XML_DECLARATION + b'\r\n'),
                         f'{name}: requires Vortex-compatible double-quoted UTF-8 declaration')
            xml_documents[name] = ET.fromstring(raw)
        if not report.ok:
            return report
        config = xml_documents['fomod/ModuleConfig.xml']
        info = xml_documents['fomod/info.xml']
        report.check(info.findtext('Version') == version, 'FOMOD/info build version mismatch')
        # Strictly limit the installer language: an unexpected required or
        # conditional install must not bypass selected-mode validation.
        browser_included = 'browserIntegration' in build
        guide_included = 'fieldGuide' in build
        kicker_included = 'jaxonzKicker' in build
        guide_payload = validate_guide_component(view, build, report)
        kicker_payload = validate_kicker_component(view, build, report)
        if browser_included:
            browser_metadata = build['browserIntegration']
            for name in ('docs/OpenMCM-Browser.md', 'LICENSE-OpenMCMBrowser-GPL-3.0.txt',
                         browser_metadata['sourceArchive']):
                report.check(view.get(name) is not None, f'Missing browser source/licence/guide: {name}')
            source_entry = view.get(browser_metadata['sourceArchive'])
            if source_entry is not None:
                report.check(hashlib.sha256(view.read_bytes(source_entry)).hexdigest().upper() ==
                             browser_metadata['sourceSha256'], 'Browser corresponding source checksum mismatch')
            report.check(browser_metadata.get('registryLimit') == 128,
                         'Browser must not claim an expanded Helper-compatible registry')
        expected = create_module_config(version, include_native=True,
                                        include_browser=browser_included,
                                        include_field_guide=guide_included,
                                        include_kicker=kicker_included).getroot()
        report.check(xml_shape(config) == xml_shape(expected),
                     'Installer differs from validated mode/detection/native schema')
        for entry in view.entries:
            report.check(not entry.key.startswith('data/'),
                         f'Unconditional Data tree would bypass mode choice: {entry.name}')
            report.check(PurePosixPath(entry.key).suffix not in ('.exe', '.pdb', '.log', '.pyc'),
                         f'Build/diagnostic file in installer: {entry.name}')
            report.check(not (entry.key.startswith('modes/') and '/data/skse/' in entry.key),
                         f'omitted native component leaked files in mode: {entry.name}')
        if not report.ok:
            return report
        groups = config.findall('./installSteps/installStep/optionalFileGroups/group')
        choices = [group.findall('./plugins/plugin') for group in groups]
        for selected in itertools.product(*choices):
            label = ' / '.join(item.attrib['name'] for item in selected)
            files: dict[str, tuple[str, bytes]] = {}
            with tempfile.TemporaryDirectory(prefix='openmcm-fomod-verify-') as temporary:
                install = Path(temporary) / 'selected'
                data = install / 'Data'
                # Preserve the strict host validator's allowlist. The sample is
                # a separate validated consumer, never an additional host file.
                host = Path(temporary) / 'host'
                host_data = host / 'Data'
                for option in selected:
                    for folder in option.findall('./files/folder'):
                        prefix = folder.attrib['source'].replace('\\', '/').rstrip('/') + '/'
                        assert folder.attrib['destination'] == ''
                        matched = [entry for entry in view.entries if entry.key.startswith(prefix.casefold())]
                        report.check(bool(matched), f'{label}: empty/missing source folder {prefix}')
                        for entry in matched:
                            relative = entry.name[len(prefix):]
                            parts = PurePosixPath(relative).parts
                            if not parts or any(part in ('', '.', '..') or ':' in part for part in parts):
                                report.check(False, f'Unsafe projected path: {relative}')
                                continue
                            key = relative.casefold()
                            if key in files:
                                report.check(False, f'Duplicate selected destination: {relative}')
                                continue
                            raw = view.read_bytes(entry)
                            files[key] = (relative, raw)
                            destination = data.joinpath(*parts)
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            destination.write_bytes(raw)
                            if key not in GUIDE_DATA_RELATIVE and key not in KICKER_FILES:
                                host_destination = host_data.joinpath(*parts)
                                host_destination.parent.mkdir(parents=True, exist_ok=True)
                                host_destination.write_bytes(raw)
                if not report.ok:
                    continue
                # Choose the contract from the XML branch, never from possibly
                # corrupted payload contents that could silently select another ABI.
                mode_source = selected[0].find('./files/folder').attrib['source']
                coexist = mode_source == 'modes/skyui/Data'
                report.check(('openmcm.esp' in files) == coexist,
                             f'{label}: companion plugin disagrees with selected mode')
                report.check(('skyui_se.esp' in files) != coexist,
                             f'{label}: standalone plugin disagrees with selected mode')
                guide_selected = any(folder.attrib['source'] == FIELD_GUIDE_PATH
                                     for option in selected for folder in option.findall('./files/folder'))
                selected_guide = {key: value[1] for key, value in files.items()
                                  if key in GUIDE_DATA_RELATIVE}
                report.check(selected_guide == (guide_payload if guide_selected else {}),
                             f'{label}: Field Guide payload differs from selected optional component')
                kicker_selected = any(folder.attrib['source'] == KICKER_PATH
                                      for option in selected for folder in option.findall('./files/folder'))
                selected_kicker = {key: value[1] for key, value in files.items() if key in KICKER_FILES}
                report.check(selected_kicker == (kicker_payload if kicker_selected else {}),
                             f'{label}: Jaxonz MCM Kicker payload differs from selected optional component')
                result = (validate_coexist(host) if coexist else
                          validate_standalone(host, default_manifest(), 'release'))
                report.checks += result.checks
                report.errors.extend(f'{label}: {error}' for error in result.errors)
                if not coexist:
                    api_result = validate_api(host)
                    report.checks += api_result.checks
                    report.errors.extend(f'{label}: {error}' for error in api_result.errors)
                native = 'skse/plugins/openmcmruntime.dll' in files
                if native:
                    metadata = validate_native(install)
                    major, minor, patch = map(int, version.split('-')[0].split('.'))
                    expected_version = major << 24 | minor << 16 | patch << 4
                    report.check(metadata['plugin_version'] == expected_version,
                                 f'{label}: incorrect native plugin version')
                    report.check(build['nativeRuntime']['pluginVersion'] == expected_version,
                                 'Build metadata native version mismatch')
                browser = 'skse/plugins/openmcmbrowser.dll' in files
                allowed_native = set()
                if native:
                    allowed_native.update(('skse/plugins/openmcmruntime.dll', 'skse/plugins/openmcmruntime.ini'))
                if browser:
                    from check_browser_native import validate_dll as validate_browser_dll
                    validate_browser_dll(files['skse/plugins/openmcmbrowser.dll'][1])
                    allowed_native.add('skse/plugins/openmcmbrowser.dll')
                    report.check(browser_included, f'{label}: browser DLL missing build metadata')
                    report.check(hashlib.sha256(files['skse/plugins/openmcmbrowser.dll'][1]).hexdigest().upper() ==
                                 build['browserIntegration']['dllSha256'], f'{label}: browser DLL checksum mismatch')
                report.check({key for key in files if key.startswith('skse/')} == allowed_native,
                             f'{label}: unexpected native component files')
                if result.ok:
                    print(f'PASS selected install: {label} ({len(files)} files)')
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate_package(args.target)
    except (OSError, ValueError, KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        print(f'FOMOD validation failed: {error}', file=sys.stderr)
        return 1
    for error in report.errors:
        print(f'ERROR: {error}', file=sys.stderr)
    print(f'{"PASS" if report.ok else "FAIL"}: {report.checks} FOMOD archive/selected-install checks')
    return 0 if report.ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
