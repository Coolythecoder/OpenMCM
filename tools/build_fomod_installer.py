#!/usr/bin/env python3
"""Assemble one OpenMCM XML FOMOD from already-validated Data trees.

Never inspects or modifies an installed game, downloads SkyUI, or removes output.
The caller owns compiled-artifact validation, root documentation, checksums and ZIP.
XML follows Nexus-Mods/fomod-installer's XmlScript5.0.xsd at commit
5f0baede15f9e6d38065b05698a358975b1f5eb9. Recommended is an initial selection,
not a lock: users can override detection when their manager cannot see SkyUI.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


XSI = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_URL = "http://qconsulting.ca/fo3/ModConfig5.0.xsd"
XML_DECLARATION = b'<?xml version="1.0" encoding="utf-8"?>'
MODE_PATHS = {
    "standalone": "modes/standalone/Data",
    "skyui": "modes/skyui/Data",
}
NATIVE_PATH = "components/native/Data"
NATIVE_FILES = {
    "skse/plugins/openmcmruntime.dll", "skse/plugins/openmcmruntime.ini",
}
BROWSER_PATH = "components/browser/Data"
BROWSER_FILES = {"skse/plugins/openmcmbrowser.dll"}
FIELD_GUIDE_PATH = "components/field-guide/Data"
FIELD_GUIDE_DOCS = "examples/field-guide"
KICKER_PATH = "components/jaxonz-kicker/Data"
KICKER_PLUGIN = "JaxonzMCMKicker.esp"
KICKER_FILES = {
    "scripts/jaxonzmcmkicker.pex", "scripts/jaxonzskseversioncheckscript.pex",
    "source/scripts/jaxonzmcmkicker.psc", "source/scripts/jaxonzskseversioncheckscript.psc",
}
KICKER_WARNING = (
    "Optional compatibility add-on for Jaxonz MCM Kicker SE in standalone or "
    "SkyUI mode. Install the original mod separately and enable "
    "JaxonzMCMKicker.esp; this add-on includes no original plugin or BSA and "
    "adds no ESP or DLL. Let OpenMCM win conflicts for JaxonzMCMKicker.pex "
    "and JaxonzSKSEVersionCheckScript.pex. Use the matching OpenMCM host from "
    "this installer. It confirms the manager reset through a Boolean result, "
    "with bounded retries if busy and deferral while Journal or RaceSexMenu "
    "is open. Provider re-registration completes asynchronously. Detection "
    "recommends installation when the original plugin is present; you may "
    "override it manually. See docs/Jaxonz-MCM-Kicker.md. Automated checks "
    "do not replace live in-game testing, which is still required."
)
FIELD_GUIDE_WARNING = (
    "Optional practical API example: a trip planner with carry-weight readouts, "
    "a checklist, preferences and an unbound-by-default summary hotkey. "
    "Enable OpenMCM_FieldGuide.esp after SkyUI_SE.esp. Enable OpenMCM API under "
    "OpenMCM > Status > Runtime to try its extensions; ordinary controls work "
    "with that switch off. Source, editable plugin and author guide are always "
    "included in examples/field-guide. No extra download or native component "
    "is required. Use a development profile for experimentation; this example "
    "has automated verification but still needs in-game testing."
)
BROWSER_WARNING = (
    "The browser works without this DLL and saves preferences with your game. "
    "This optional component shares browser favourites, hidden entries, labels "
    "and priorities between characters. It does not export mod settings or "
    "expand the 128-menu registry. Requires matching SKSE and Address Library "
    "on a supported runtime; see the browser guide. Experimental, not yet "
    "verified in game. Do not install MCM Menu Redone alongside OpenMCM."
)
DETECTION_WARNING = (
    "Detection recommends a mode using SkyUI's archive or loose files, not "
    "SkyUI_SE.esp alone (standalone OpenMCM uses that name too). If SkyUI is "
    "not deployed or the mod manager cannot see its BSA/loose files, choose "
    "the correct mode manually. Detection does not verify a SkyUI version. "
    "Switching modes on an existing save is not a verified migration; use "
    "the documented profile/save guidance."
)
NATIVE_WARNING = (
    "Optional character-creation precache component, not required for MCM. "
    "Skyrim 1.7.104.0 ONLY; omit on every other runtime. This has automated "
    "verification only and is not a confirmed fix for the exit-to-desktop "
    "crash. Preserve custom OpenMCMRuntime.ini settings and any intentional "
    "DLL omission when updating."
)


def _present(parent: ET.Element, filename: str) -> None:
    """Presence includes inactive plugins; enabling is an installation instruction."""
    group = ET.SubElement(parent, "dependencies", operator="Or")
    for state in ("Active", "Inactive"):
        ET.SubElement(group, "fileDependency", file=filename, state=state)


def _skyui_condition(parent: ET.Element) -> None:
    condition = ET.SubElement(parent, "dependencies", operator="And")
    _present(condition, "SkyUI_SE.esp")
    markers = ET.SubElement(condition, "dependencies", operator="Or")
    _present(markers, "SkyUI_SE.bsa")
    loose = ET.SubElement(markers, "dependencies", operator="And")
    _present(loose, "Scripts\\SKI_Main.pex")
    _present(loose, "Interface\\skyui\\config.txt")


def _conditional_type(plugin: ET.Element, *, skyui: bool) -> None:
    descriptor = ET.SubElement(plugin, "typeDescriptor")
    dependency = ET.SubElement(descriptor, "dependencyType")
    ET.SubElement(dependency, "defaultType", name="Optional" if skyui else "Recommended")
    pattern = ET.SubElement(ET.SubElement(dependency, "patterns"), "pattern")
    _skyui_condition(pattern)
    ET.SubElement(pattern, "type", name="Recommended" if skyui else "Optional")


def _kicker_type(plugin: ET.Element, *, include: bool) -> None:
    descriptor = ET.SubElement(plugin, "typeDescriptor")
    dependency = ET.SubElement(descriptor, "dependencyType")
    ET.SubElement(dependency, "defaultType", name="Optional" if include else "Recommended")
    pattern = ET.SubElement(ET.SubElement(dependency, "patterns"), "pattern")
    _present(pattern, KICKER_PLUGIN)
    ET.SubElement(pattern, "type", name="Recommended" if include else "Optional")


def _plugin(parent: ET.Element, name: str, description: str,
            source: str | None = None) -> ET.Element:
    plugin = ET.SubElement(parent, "plugin", name=name)
    ET.SubElement(plugin, "description").text = description
    if source is not None:
        files = ET.SubElement(plugin, "files")
        # The manager's installation root is Data: never create a nested Data/Data.
        ET.SubElement(files, "folder", source=source, destination="")
    return plugin


def create_module_config(version: str, *, include_native: bool,
                         include_browser: bool = False,
                         include_field_guide: bool = False,
                         include_kicker: bool = False) -> ET.ElementTree:
    """Create deterministic XML, with exactly one recommended option per group."""
    _validate_version(version)
    ET.register_namespace("xsi", XSI)
    root = ET.Element("config", {f"{{{XSI}}}noNamespaceSchemaLocation": SCHEMA_URL})
    ET.SubElement(root, "moduleName").text = f"OpenMCM {version}"
    steps = ET.SubElement(root, "installSteps", order="Explicit")
    step = ET.SubElement(steps, "installStep", name="MCM host mode")
    groups = ET.SubElement(step, "optionalFileGroups", order="Explicit")
    group = ET.SubElement(groups, "group", name="Choose one installation mode",
                          type="SelectExactlyOne")
    plugins = ET.SubElement(group, "plugins", order="Explicit")
    standalone = _plugin(
        plugins, "Standalone - no SkyUI",
        "Use OpenMCM without SkyUI. Includes the standalone SkyUI_SE.esp "
        "compatibility plugin; do not enable the real SkyUI alongside this "
        "mode. Keep SkyUI_SE.esp enabled and launch through SKSE. Replace the "
        "previous OpenMCM package and disable old mouse/diagnostic add-ons. "
        + DETECTION_WARNING,
        MODE_PATHS["standalone"],
    )
    _conditional_type(standalone, skyui=False)
    skyui = _plugin(
        plugins, "With SkyUI - OpenMCM hosts MCM",
        "Keep the actual SkyUI installed for its other interfaces; OpenMCM "
        "remains the MCM host. This mode does not supply SkyUI. Enable the "
        "real SkyUI_SE.esp and the included coexistence plugin, and let "
        "OpenMCM win its MCM-script and Journal conflicts. SKSE is required. "
        "Install MCM Helper separately when a provider requires it. "
        + DETECTION_WARNING,
        MODE_PATHS["skyui"],
    )
    _conditional_type(skyui, skyui=True)
    if include_native:
        step = ET.SubElement(steps, "installStep", name="Optional native component")
        groups = ET.SubElement(step, "optionalFileGroups", order="Explicit")
        group = ET.SubElement(groups, "group", name="Character-creation precache component",
                              type="SelectExactlyOne")
        plugins = ET.SubElement(group, "plugins", order="Explicit")
        omit = _plugin(plugins, "Omit native component (recommended)", NATIVE_WARNING)
        ET.SubElement(ET.SubElement(omit, "typeDescriptor"), "type", name="Recommended")
        include = _plugin(plugins, "Include native component - Skyrim 1.7.104.0 only",
                          NATIVE_WARNING, NATIVE_PATH)
        ET.SubElement(ET.SubElement(include, "typeDescriptor"), "type", name="Optional")
    if include_browser:
        step = ET.SubElement(steps, "installStep", name="Browser preference storage")
        groups = ET.SubElement(step, "optionalFileGroups", order="Explicit")
        group = ET.SubElement(groups, "group", name="Browser preferences",
                              type="SelectExactlyOne")
        plugins = ET.SubElement(group, "plugins", order="Explicit")
        local = _plugin(plugins, "Save-local preferences (recommended)", BROWSER_WARNING)
        ET.SubElement(ET.SubElement(local, "typeDescriptor"), "type", name="Recommended")
        shared = _plugin(plugins, "Shared browser preferences - optional native component",
                         BROWSER_WARNING, BROWSER_PATH)
        ET.SubElement(ET.SubElement(shared, "typeDescriptor"), "type", name="Optional")
    if include_field_guide:
        step = ET.SubElement(steps, "installStep", name="Practical API example")
        groups = ET.SubElement(step, "optionalFileGroups", order="Explicit")
        group = ET.SubElement(groups, "group", name="OpenMCM Field Guide",
                              type="SelectExactlyOne")
        plugins = ET.SubElement(group, "plugins", order="Explicit")
        omit = _plugin(plugins, "Do not install example (recommended)", FIELD_GUIDE_WARNING)
        ET.SubElement(ET.SubElement(omit, "typeDescriptor"), "type", name="Recommended")
        include = _plugin(plugins, "Install Field Guide - practical API example",
                          FIELD_GUIDE_WARNING, FIELD_GUIDE_PATH)
        ET.SubElement(ET.SubElement(include, "typeDescriptor"), "type", name="Optional")
    if include_kicker:
        step = ET.SubElement(steps, "installStep", name="Jaxonz MCM Kicker compatibility")
        groups = ET.SubElement(step, "optionalFileGroups", order="Explicit")
        group = ET.SubElement(groups, "group", name="Jaxonz MCM Kicker SE",
                              type="SelectExactlyOne")
        plugins = ET.SubElement(group, "plugins", order="Explicit")
        omit = _plugin(plugins, "Do not install Jaxonz MCM Kicker compatibility", KICKER_WARNING)
        _kicker_type(omit, include=False)
        include = _plugin(plugins, "Install Jaxonz MCM Kicker compatibility",
                          KICKER_WARNING, KICKER_PATH)
        _kicker_type(include, include=True)
    ET.indent(root, space="  ")
    return ET.ElementTree(root)


def _validate_version(version: str) -> None:
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z]+(?:[.-][0-9A-Za-z]+)*)?", version):
        raise ValueError("Version must be a numeric major.minor.patch with optional prerelease")


def write_installer_xml(tree: ET.ElementTree, path: Path) -> None:
    """Write UTF-8 with a declaration accepted by Nexus's StringStream reader.

    ElementTree's single-quoted encoding declaration is legal XML, but Nexus
    XmlScriptType.StringStream only removes double-quoted encoding attributes
    before transcoding the string to UTF-16BE. A surviving UTF-8 declaration
    therefore makes Vortex fail at line 1, column 39. Keep the body untouched;
    do not globally replace apostrophes in author-facing content.
    Source: Nexus-Mods/fomod-installer, commit
    5f0baede15f9e6d38065b05698a358975b1f5eb9, XmlScriptType.cs/StringStream.
    """
    body = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=False)
    path.write_bytes(XML_DECLARATION + b"\n" + body)


def _inventory(root: Path) -> dict[str, Path]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"Input must be a real Data directory: {root}")
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError(f"Linked input is not allowed: {path}")
        if not path.is_file():
            continue
        name = path.relative_to(root).as_posix()
        if any(part in (".", "..", "") or ":" in part or "\\" in part
               for part in name.split("/")):
            raise ValueError(f"Unsafe input path: {name}")
        key = name.casefold()
        if key in files:
            raise ValueError(f"Case-insensitive duplicate input path: {name}")
        files[key] = path
    if not files:
        raise ValueError(f"Input Data directory is empty: {root}")
    return files


def _validate_mode(files: dict[str, Path], *, skyui: bool) -> None:
    required = {"interface/quest_journal.swf", "scripts/ski_configbase.pex",
                "scripts/ski_configmanager.pex"}
    if not skyui:
        required.update({"skyui_se.esp", "seq/skyui_se.seq"})
    if missing := required - files.keys():
        raise ValueError(f"Mode is missing required files: {', '.join(sorted(missing))}")
    for key in files:
        if (key.endswith(".bsa") or key.startswith("interface/skyui/")
                or key == "scripts/ski_main.pex"):
            raise ValueError(f"Do not copy SkyUI archives/assets/scripts into this installer: {key}")
        if key.startswith("skse/"):
            raise ValueError(f"Keep native files outside both mode Data trees: {key}")
        if "openmcm_fieldguide" in key:
            raise ValueError(f"Keep the optional Field Guide outside both mode Data trees: {key}")
        if "jaxonzmcmkicker" in key or "jaxonzskseversioncheckscript" in key:
            raise ValueError(f"Keep optional Jaxonz MCM Kicker files outside both mode Data trees: {key}")
        if skyui and key in {"skyui_se.esp", "seq/skyui_se.seq"}:
            raise ValueError(f"SkyUI mode must not replace the actual SkyUI plugin/SEQ: {key}")
    if skyui and not any("/" not in key and key.endswith((".esp", ".esl")) for key in files):
        raise ValueError("SkyUI mode must contain its distinct coexistence plugin")


def build_installer(standalone_data: Path, skyui_data: Path, output: Path,
                    version: str, native_data: Path | None = None,
                    browser_data: Path | None = None,
                    field_guide_package: Path | None = None,
                    kicker_data: Path | None = None) -> Path:
    """Copy validated-input inventories into a NEW/empty full-installer root.

    Inputs are Data-shaped folders. Native input, if supplied, must contain only
    SKSE/Plugins/OpenMCMRuntime.dll and OpenMCMRuntime.ini. Browser input must
    contain only SKSE/Plugins/OpenMCMBrowser.dll; it is a separate choice.
    No previous output is removed or overwritten. Copies preserve source bytes.
    """
    _validate_version(version)
    inputs = [Path(standalone_data), Path(skyui_data)]
    if native_data is not None:
        inputs.append(Path(native_data))
    if browser_data is not None:
        inputs.append(Path(browser_data))
    inventories = [_inventory(path) for path in inputs]
    _validate_mode(inventories[0], skyui=False)
    _validate_mode(inventories[1], skyui=True)
    if native_data is not None and set(inventories[2]) != NATIVE_FILES:
        raise ValueError("Native Data directory must contain only OpenMCMRuntime.dll and its INI")
    if browser_data is not None and set(inventories[-1]) != BROWSER_FILES:
        raise ValueError("Browser Data directory must contain only OpenMCMBrowser.dll")
    if kicker_data is not None:
        from check_kicker import validate_package as validate_kicker, validate_manager_bytes
        kicker_data = Path(kicker_data)
        kicker_files = _inventory(kicker_data)
        if set(kicker_files) != KICKER_FILES:
            raise ValueError("Kicker Data directory must contain only its two PEX and two source scripts")
        report = validate_kicker(kicker_data)
        if not report.ok:
            raise ValueError("Jaxonz MCM Kicker package invalid: " + "; ".join(report.errors))
        for host in inventories[:2]:
            manager = host.get('scripts/ski_configmanager.pex')
            source = host.get('source/scripts/ski_configmanager.psc')
            result = validate_manager_bytes(manager.read_bytes() if manager else b'',
                                            source.read_bytes() if source else b'')
            if not result.ok:
                raise ValueError('Kicker requires matching host: ' + '; '.join(result.errors))
        inputs.append(kicker_data)
        inventories.append(kicker_files)
    # Validate the complete sample, not an unchecked folder of installable files.
    # Its original manifest is kept with the author files, allowing the final
    # checker to reconstruct and verify the package after this split layout.
    guide_files = None
    if field_guide_package is not None:
        from check_field_guide import validate_package as validate_field_guide
        field_guide_package = Path(field_guide_package)
        guide_files = _inventory(field_guide_package)
        report = validate_field_guide(field_guide_package)
        if not report.ok:
            raise ValueError("Field Guide package invalid: " + "; ".join(report.errors))
    output = Path(output)
    if output.is_symlink() or (hasattr(output, "is_junction") and output.is_junction()):
        raise ValueError("Output must not be a link")
    resolved_output = output.resolve()
    for source in inputs + ([field_guide_package] if field_guide_package is not None else []):
        resolved_source = source.resolve()
        if (resolved_output.is_relative_to(resolved_source)
                or resolved_source.is_relative_to(resolved_output)):
            raise ValueError("Output and source directories must not overlap")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError(f"Output already exists and is not empty; nothing replaced: {output}")
    output.mkdir(parents=True, exist_ok=True)
    destinations = [MODE_PATHS["standalone"], MODE_PATHS["skyui"]]
    if native_data is not None:
        destinations.append(NATIVE_PATH)
    if browser_data is not None:
        destinations.append(BROWSER_PATH)
    if kicker_data is not None:
        destinations.append(KICKER_PATH)
    for source, files, destination in zip(inputs, inventories, destinations):
        for path in files.values():
            target = output / destination / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    if guide_files is not None:
        for key, path in guide_files.items():
            relative = path.relative_to(field_guide_package)
            if key.startswith("data/"):
                target = output / FIELD_GUIDE_PATH / Path(*relative.parts[1:])
            else:
                target = output / FIELD_GUIDE_DOCS / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    metadata = output / "fomod"
    metadata.mkdir()
    write_installer_xml(create_module_config(version, include_native=native_data is not None,
                                             include_browser=browser_data is not None,
                                             include_field_guide=guide_files is not None,
                                             include_kicker=kicker_data is not None),
                        metadata / "ModuleConfig.xml")
    info = ET.Element("fomod")
    ET.SubElement(info, "Name").text = "OpenMCM"
    ET.SubElement(info, "Version").text = version
    ET.SubElement(info, "Description").text = (
        "Standalone or alongside SkyUI, with OpenMCM as the MCM host. " + DETECTION_WARNING)
    ET.indent(info, space="  ")
    write_installer_xml(ET.ElementTree(info), metadata / "info.xml")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--standalone-data", type=Path, required=True)
    parser.add_argument("--skyui-data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--native-data", type=Path)
    parser.add_argument("--browser-data", type=Path)
    parser.add_argument("--field-guide-package", type=Path)
    parser.add_argument("--kicker-data", type=Path)
    args = parser.parse_args(argv)
    try:
        result = build_installer(args.standalone_data, args.skyui_data, args.output,
                                 args.version, args.native_data, args.browser_data,
                                 args.field_guide_package, args.kicker_data)
    except (ValueError, OSError) as error:
        print(f"FOMOD build failed: {error}", file=sys.stderr)
        return 1
    print(f"Full OpenMCM installer staged at: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
