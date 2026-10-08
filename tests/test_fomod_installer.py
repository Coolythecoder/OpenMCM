"""Exercise generated FOMOD branches and detection from actual emitted XML.

No installed game or mod-manager state is read or changed. The evaluator below
implements only the documented fileDependency/And/Or/type subset we emit.
"""

from __future__ import annotations

import itertools
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_fomod_installer import (  # noqa: E402
    DETECTION_WARNING, MODE_PATHS, NATIVE_PATH, NATIVE_WARNING, BROWSER_PATH,
    KICKER_PATH, KICKER_FILES, KICKER_PLUGIN, KICKER_WARNING,
    SCHEMA_URL, XSI, build_installer, create_module_config, main, write_installer_xml,
)
from check_mcm_contract import Report  # noqa: E402


def condition_matches(element: ET.Element, states: dict[str, str]) -> bool:
    values = []
    for child in element:
        if child.tag == "fileDependency":
            key = child.attrib["file"].replace("\\", "/").casefold()
            values.append(states.get(key, "Missing") == child.attrib["state"])
        elif child.tag == "dependencies":
            values.append(condition_matches(child, states))
        else:
            raise AssertionError(f"Unsupported emitted condition: {child.tag}")
    return any(values) if element.get("operator", "And") == "Or" else all(values)


def option_type(plugin: ET.Element, states: dict[str, str]) -> str:
    descriptor = plugin.find("typeDescriptor")
    static = descriptor.find("type")
    if static is not None:
        return static.attrib["name"]
    dynamic = descriptor.find("dependencyType")
    for pattern in dynamic.findall("patterns/pattern"):
        if condition_matches(pattern.find("dependencies"), states):
            return pattern.find("type").attrib["name"]
    return dynamic.find("defaultType").attrib["name"]


class FomodXMLTests(unittest.TestCase):
    def setUp(self):
        self.root = create_module_config("1.2.0-rc.1", include_native=True).getroot()
        self.groups = self.root.findall("installSteps/installStep/optionalFileGroups/group")
        self.modes = self.groups[0].findall("plugins/plugin")

    def test_metadata_and_exactly_one_mode(self):
        self.assertEqual(self.root.get(f"{{{XSI}}}noNamespaceSchemaLocation"), SCHEMA_URL)
        self.assertEqual(self.root.findtext("moduleName"), "OpenMCM 1.2.0-rc.1")
        self.assertEqual([group.get("type") for group in self.groups],
                         ["SelectExactlyOne", "SelectExactlyOne"])
        self.assertEqual(len(self.modes), 2)
        self.assertIsNone(self.root.find("requiredInstallFiles"))
        self.assertIsNone(self.root.find("conditionalFileInstalls"))

    def test_browser_creates_independent_optional_choice_and_eight_combinations(self):
        root = create_module_config("1.2.0-alpha.5", include_native=True, include_browser=True).getroot()
        groups = root.findall("installSteps/installStep/optionalFileGroups/group")
        self.assertEqual([item.get("type") for item in groups], ["SelectExactlyOne"] * 3)
        choices = [item.findall("plugins/plugin") for item in groups]
        self.assertEqual(len(list(itertools.product(*choices))), 8)
        self.assertEqual([option_type(item, {}) for item in choices[2]], ["Recommended", "Optional"])
        self.assertIsNone(choices[2][0].find("files"))
        self.assertEqual(choices[2][1].find("files/folder").get("source"), BROWSER_PATH)
        for selection in itertools.product(*choices):
            sources = [node.get("source") for item in selection for node in item.findall("files/folder")]
            self.assertEqual(sum(source in MODE_PATHS.values() for source in sources), 1)
            self.assertEqual(len(sources), len(set(sources)))

    def test_detection_truth_table_all_81_states(self):
        keys = ["skyui_se.esp", "skyui_se.bsa", "scripts/ski_main.pex",
                "interface/skyui/config.txt"]
        for combination in itertools.product(("Missing", "Active", "Inactive"), repeat=4):
            with self.subTest(combination=combination):
                states = dict(zip(keys, combination))
                present = [state != "Missing" for state in combination]
                detected = present[0] and (present[1] or (present[2] and present[3]))
                types = [option_type(plugin, states) for plugin in self.modes]
                self.assertEqual(types, ["Optional", "Recommended"] if detected
                                 else ["Recommended", "Optional"])
                self.assertEqual(types.count("Recommended"), 1)
                self.assertEqual(types.count("Optional"), 1)  # manual override always possible

    def test_kicker_adds_fifth_independent_choice_and_32_combinations(self):
        root = create_module_config("1.2.0", include_native=True, include_browser=True,
                                    include_field_guide=True, include_kicker=True).getroot()
        groups = root.findall("installSteps/installStep/optionalFileGroups/group")
        self.assertEqual([group.get("type") for group in groups], ["SelectExactlyOne"] * 5)
        choices = [group.findall("plugins/plugin") for group in groups]
        self.assertEqual(len(list(itertools.product(*choices))), 32)
        options = choices[4]
        self.assertIsNone(options[0].find("files"))
        self.assertEqual(options[1].find("files/folder").attrib,
                         {"source": KICKER_PATH, "destination": ""})
        for state in ("Missing", "Active", "Inactive"):
            types = [option_type(option, {KICKER_PLUGIN.casefold(): state}) for option in options]
            self.assertEqual(types, ["Recommended", "Optional"] if state == "Missing"
                             else ["Optional", "Recommended"])
        for option in options:
            self.assertIn(KICKER_WARNING, option.findtext("description"))

    def test_kicker_selection_is_independent_of_skyui_detection(self):
        root = create_module_config("1.2.0", include_native=False, include_kicker=True).getroot()
        groups = root.findall("installSteps/installStep/optionalFileGroups/group")
        options = groups[1].findall("plugins/plugin")
        for skyui in ("Missing", "Active", "Inactive"):
            for kicker in ("Missing", "Active", "Inactive"):
                states = {"skyui_se.esp": skyui, "skyui_se.bsa": skyui,
                          KICKER_PLUGIN.casefold(): kicker}
                self.assertEqual(option_type(options[1], states),
                                 "Optional" if kicker == "Missing" else "Recommended")

    def test_standalone_plugin_alone_is_not_detected_as_skyui(self):
        for state in ("Active", "Inactive"):
            self.assertEqual(option_type(self.modes[0], {"skyui_se.esp": state}), "Recommended")
            self.assertEqual(option_type(self.modes[1], {"skyui_se.esp": state}), "Optional")

    def test_native_is_omitted_by_default_and_not_in_mode_mapping(self):
        options = self.groups[1].findall("plugins/plugin")
        self.assertEqual([option_type(item, {}) for item in options], ["Recommended", "Optional"])
        self.assertIsNone(options[0].find("files"))
        self.assertEqual(options[1].find("files/folder").get("source"), NATIVE_PATH)
        for plugin, expected in zip(self.modes, MODE_PATHS.values()):
            folders = plugin.findall("files/folder")
            self.assertEqual(len(folders), 1)
            self.assertEqual(folders[0].attrib, {"source": expected, "destination": ""})

    def test_payloads_selected_from_exactly_one_disjoint_source_branch(self):
        sources = [plugin.find("files/folder").get("source") for plugin in self.modes]
        self.assertNotEqual(sources[0], sources[1])
        for source in sources:
            self.assertNotIn("..", Path(source).parts)
            self.assertFalse(Path(source).is_absolute())
        for mode in self.modes:
            for native in self.groups[1].findall("plugins/plugin"):
                mappings = [item for selected in (mode, native)
                            for item in selected.findall("files/folder")]
                self.assertEqual(sum(item.get("source") in MODE_PATHS.values()
                                     for item in mappings), 1)
                self.assertTrue(all(item.get("destination") == "" for item in mappings))

    def test_limitations_are_visible_for_each_mode(self):
        for plugin in self.modes:
            self.assertIn(DETECTION_WARNING, plugin.findtext("description"))
        for plugin in self.groups[1].findall("plugins/plugin"):
            self.assertIn(NATIVE_WARNING, plugin.findtext("description"))
        self.assertIn("Enable the real SkyUI_SE.esp", self.modes[1].findtext("description"))

    def test_no_native_step_if_payload_not_supplied(self):
        root = create_module_config("1.2.0", include_native=False).getroot()
        self.assertEqual(len(root.findall("installSteps/installStep")), 1)
        self.assertNotIn(NATIVE_PATH, ET.tostring(root, encoding="unicode"))

    def test_invalid_versions_rejected(self):
        for version in ("", "../1.2.0", "1.2", "1.2.0/evil", '1.2.0"', "1.2.0\n"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                create_module_config(version, include_native=False)


class FomodBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.standalone = self.work / "standalone" / "Data"
        self.skyui = self.work / "skyui" / "Data"
        self.native = self.work / "native" / "Data"
        self.output = self.work / "installer"
        for folder in (self.standalone, self.skyui):
            self.put(folder, "Interface/quest_journal.swf", b"shared swf")
            self.put(folder, "Scripts/SKI_ConfigBase.pex", b"shared base")
            self.put(folder, "Scripts/SKI_ConfigManager.pex", b"shared manager")
        self.put(self.standalone, "SkyUI_SE.esp", b"standalone identity")
        self.put(self.standalone, "Seq/SkyUI_SE.seq", b"standalone seq")
        self.put(self.skyui, "OpenMCM_SkyUI.esp", b"coexistence patch")
        self.put(self.skyui, "Seq/OpenMCM_SkyUI.seq", b"coexistence seq")
        self.put(self.native, "SKSE/Plugins/OpenMCMRuntime.dll", b"optional dll")
        self.put(self.native, "SKSE/Plugins/OpenMCMRuntime.ini", b"[Patches]\nDisableChargenPrecache=0\n")

    @staticmethod
    def put(root: Path, path: str, content: bytes) -> None:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def build(self, **kwargs) -> Path:
        return build_installer(self.standalone, self.skyui, self.output, "1.2.0", **kwargs)

    def test_build_preserves_all_bytes_in_both_modes_and_native(self):
        self.assertEqual(self.build(native_data=self.native), self.output)
        for source, destination in ((self.standalone, MODE_PATHS["standalone"]),
                                    (self.skyui, MODE_PATHS["skyui"]),
                                    (self.native, NATIVE_PATH)):
            for original in source.rglob("*"):
                if original.is_file():
                    self.assertEqual(original.read_bytes(),
                                     (self.output / destination / original.relative_to(source)).read_bytes())
        root = ET.parse(self.output / "fomod/ModuleConfig.xml").getroot()
        for mapping in root.findall(".//files/folder"):
            self.assertTrue((self.output / mapping.get("source")).is_dir())
        self.assertEqual(ET.parse(self.output / "fomod/info.xml").findtext("Version"), "1.2.0")
        self.assertFalse((self.output / "Data").exists())
        self.assertFalse((self.output / MODE_PATHS["skyui"] / "SkyUI_SE.esp").exists())

    def test_existing_nonempty_output_is_preserved(self):
        self.put(self.output, "existing-release.txt", b"keep this")
        with self.assertRaisesRegex(ValueError, "not empty"):
            self.build()
        self.assertEqual((self.output / "existing-release.txt").read_bytes(), b"keep this")
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_both_xml_files_use_vortex_compatible_declarations(self):
        self.build()
        # Literal expected bytes deliberately do not reuse the writer constant.
        for name in ("ModuleConfig.xml", "info.xml"):
            with self.subTest(name=name):
                raw = (self.output / "fomod" / name).read_bytes()
                self.assertTrue(raw.startswith(b'<?xml version="1.0" encoding="utf-8"?>\n'))
                self.assertNotIn(b"\x00", raw)
                self.assertEqual(raw.decode("utf-8").encode("utf-8"), raw)

    def test_serialization_preserves_unicode_apostrophes_and_xml_escaping(self):
        value = "Author's MCM: café — 色 & <settings>"
        tree = ET.ElementTree(ET.Element("fomod"))
        ET.SubElement(tree.getroot(), "Description").text = value
        path = self.work / "info.xml"
        write_installer_xml(tree, path)
        self.assertEqual(ET.parse(path).findtext("Description"), value)
        self.assertIn(b"Author's", path.read_bytes())
        self.assertIn(b"&amp; &lt;settings&gt;", path.read_bytes())

    def test_existing_empty_output_is_allowed(self):
        self.output.mkdir()
        self.build()
        self.assertTrue((self.output / "fomod/ModuleConfig.xml").is_file())

    def test_overlapping_output_is_rejected_before_writes(self):
        for output in (self.standalone, self.standalone / "nested", self.work):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "overlap"):
                build_installer(self.standalone, self.skyui, output, "1.2.0")
        self.assertFalse((self.standalone / "nested").exists())

    def test_skyui_mode_cannot_replace_original_plugin(self):
        self.put(self.skyui, "SkyUI_SE.esp", b"wrong")
        with self.assertRaisesRegex(ValueError, "must not replace"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_skyui_assets_cannot_be_bundled(self):
        for path in ("SkyUI_SE.bsa", "Interface/skyui/configpanel.swf", "Scripts/SKI_Main.pex"):
            target = self.standalone / path
            with self.subTest(path=path):
                self.put(self.standalone, path, b"forbidden")
                with self.assertRaisesRegex(ValueError, "SkyUI archives/assets/scripts"):
                    self.build()
                self.assertFalse(self.output.exists())
                target.unlink()

    def test_native_must_not_leak_into_either_mode(self):
        for source in (self.standalone, self.skyui):
            with self.subTest(source=source):
                target = source / "SKSE/Plugins/OpenMCMRuntime.dll"
                self.put(source, "SKSE/Plugins/OpenMCMRuntime.dll", b"wrong branch")
                with self.assertRaisesRegex(ValueError, "outside both mode"):
                    self.build()
                target.unlink()

    def test_native_input_inventory_is_exact(self):
        self.put(self.native, "SKSE/Plugins/unrelated.dll", b"not OpenMCM")
        with self.assertRaisesRegex(ValueError, "must contain only"):
            self.build(native_data=self.native)
        self.assertFalse(self.output.exists())

    def test_browser_payload_is_separate_with_or_without_chargen(self):
        browser = self.work / "browser" / "Data"
        self.put(browser, "SKSE/Plugins/OpenMCMBrowser.dll", b"browser fixture")
        for native in (None, self.native):
            output = self.work / ("with-chargen" if native else "without-chargen")
            build_installer(self.standalone, self.skyui, output, "1.2.0-alpha.5", native, browser)
            self.assertEqual((output / BROWSER_PATH / "SKSE/Plugins/OpenMCMBrowser.dll").read_bytes(), b"browser fixture")
            self.assertEqual((output / NATIVE_PATH).exists(), native is not None)
            self.assertFalse((output / MODE_PATHS['standalone'] / 'SKSE').exists())
            self.assertFalse((output / MODE_PATHS['skyui'] / 'SKSE').exists())

    def test_browser_inventory_rejects_other_plugins_and_configs(self):
        browser = self.work / "browser" / "Data"
        self.put(browser, "SKSE/Plugins/OpenMCMBrowser.dll", b"browser fixture")
        self.put(browser, "SKSE/Plugins/unrelated.ini", b"unexpected")
        with self.assertRaisesRegex(ValueError, "Browser Data directory must contain only"):
            self.build(browser_data=browser)
        self.assertFalse(self.output.exists())

    def kicker_fixture(self):
        data = self.work / "kicker" / "Data"
        for name in KICKER_FILES:
            self.put(data, name, ("kicker fixture: " + name).encode())
        patcher = mock.patch('check_kicker.validate_manager_bytes',
                             return_value=Report('host fixture', 'kicker-host'))
        self.kicker_host_mock = patcher.start()
        self.addCleanup(patcher.stop)
        return data

    def test_kicker_rejects_old_host_without_completion_method(self):
        kicker = self.kicker_fixture()
        self.kicker_host_mock.return_value = Report('old host', 'kicker-host', errors=['missing acknowledgement'])
        with mock.patch('check_kicker.validate_package', return_value=Report('adapter', 'kicker')):
            with self.assertRaisesRegex(ValueError, 'Kicker requires matching host'):
                self.build(kicker_data=kicker)
        self.assertFalse(self.output.exists())

    def test_kicker_payload_is_separate_with_each_native_browser_combination(self):
        kicker = self.kicker_fixture()
        browser = self.work / "browser" / "Data"
        self.put(browser, "SKSE/Plugins/OpenMCMBrowser.dll", b"browser fixture")
        for native, browser_choice in itertools.product((None, self.native), (None, browser)):
            output = self.work / f"kicker-{bool(native)}-{bool(browser_choice)}"
            with mock.patch("check_kicker.validate_package", return_value=Report(str(kicker), "kicker")) as check:
                build_installer(self.standalone, self.skyui, output, "1.2.0", native,
                                 browser_choice, kicker_data=kicker)
            check.assert_called_once_with(kicker)
            actual = {path.relative_to(output / KICKER_PATH).as_posix().casefold(): path.read_bytes()
                      for path in (output / KICKER_PATH).rglob("*") if path.is_file()}
            self.assertEqual(actual, {name: (kicker / name).read_bytes() for name in KICKER_FILES})
            self.assertEqual((output / NATIVE_PATH).exists(), native is not None)
            self.assertEqual((output / BROWSER_PATH).exists(), browser_choice is not None)
            for mode in MODE_PATHS.values():
                self.assertFalse(any("jaxonz" in path.name.casefold() for path in (output / mode).rglob("*")))

    def test_kicker_inventory_rejects_original_plugin_or_extra_payload(self):
        kicker = self.kicker_fixture()
        for extra in (KICKER_PLUGIN, "JaxonzMCMKicker.bsa", "SKSE/Plugins/extra.dll"):
            with self.subTest(extra=extra):
                self.put(kicker, extra, b"unexpected")
                with self.assertRaisesRegex(ValueError, "Kicker Data directory must contain only"):
                    self.build(kicker_data=kicker)
                self.assertFalse(self.output.exists())
                (kicker / extra).unlink()

    def test_kicker_invalid_compiled_contract_blocks_copy(self):
        kicker = self.kicker_fixture()
        failure = Report(str(kicker), "kicker", errors=["invalid compiled refresh contract"])
        with mock.patch("check_kicker.validate_package", return_value=failure):
            with self.assertRaisesRegex(ValueError, "invalid compiled refresh contract"):
                self.build(kicker_data=kicker)
        self.assertFalse(self.output.exists())

    def test_kicker_must_not_leak_into_host_modes(self):
        for source in (self.standalone, self.skyui):
            self.put(source, "Scripts/JaxonzMCMKicker.pex", b"wrong branch")
            with self.assertRaisesRegex(ValueError, "Kicker files outside both mode"):
                self.build()
            (source / "Scripts/JaxonzMCMKicker.pex").unlink()

    def test_kicker_cli_option(self):
        kicker = self.kicker_fixture()
        with mock.patch("check_kicker.validate_package", return_value=Report(str(kicker), "kicker")):
            self.assertEqual(main(["--standalone-data", str(self.standalone),
                                   "--skyui-data", str(self.skyui), "--output", str(self.output),
                                   "--version", "1.2.0", "--kicker-data", str(kicker)]), 0)
        self.assertTrue((self.output / KICKER_PATH).is_dir())

    def test_missing_required_mode_file_is_rejected(self):
        (self.skyui / "Interface/quest_journal.swf").unlink()
        with self.assertRaisesRegex(ValueError, "missing required"):
            self.build()
        self.assertFalse(self.output.exists())

    def test_cli_build(self):
        self.assertEqual(main(["--standalone-data", str(self.standalone),
                               "--skyui-data", str(self.skyui), "--output", str(self.output),
                               "--version", "1.2.0"]), 0)
        self.assertFalse((self.output / NATIVE_PATH).exists())


if __name__ == "__main__":
    unittest.main()
