"""Check the independent status quest and execute its actual registration guard.

The small Papyrus conditional is translated to Python with mocked Game/Parent
APIs. This tests branch ownership, not live Papyrus or save migration.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "src/papyrus/OpenMCM_ConfigMenu.psc"
PLUGIN = ROOT / "src/plugin-coexist/OpenMCM.esp"


def registration_guard():
    source = PROVIDER.read_text(encoding="utf-8")
    event = re.search(r"(?ims)^Event OnConfigManagerReady\([^\n]+\)\s*\n(.*?)^EndEvent", source)
    if event is None:
        raise AssertionError("Missing registration event")
    lines = ["def guard():"]
    indent = 1
    for original in event.group(1).splitlines():
        line = original.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("If "):
            lines.append("    " * indent + "if " + line[3:] + ":")
            indent += 1
        elif line.startswith("ElseIf "):
            indent -= 1
            lines.append("    " * indent + "elif " + line[7:] + ":")
            indent += 1
        elif line == "EndIf":
            indent -= 1
        elif line == "Return":
            lines.append("    " * indent + "return")
        elif line == "Parent.OnConfigManagerReady(a_eventName, a_strArg, a_numArg, a_sender)":
            lines.append("    " * indent + line)
        else:
            raise AssertionError(f"Unsupported guard instruction: {line}")
    if indent != 1:
        raise AssertionError("Unbalanced registration guard")
    return compile("\n".join(lines), str(PROVIDER), "exec")


def run_guard(self, companion_index=255, companion=None, standalone=None):
    calls = []
    forwarded = []

    def lookup_mod(name):
        if name != "OpenMCM.esp":
            raise AssertionError(f"Unexpected plugin lookup: {name}")
        calls.append(("mod", name))
        return companion_index

    def lookup_form(form_id, plugin):
        calls.append(("form", form_id, plugin))
        if (form_id, plugin) == (0x800, "OpenMCM.esp"):
            return companion
        if (form_id, plugin) == (0x830, "SkyUI_SE.esp"):
            return standalone
        raise AssertionError(f"Unexpected form lookup: {form_id}, {plugin}")

    environment = {
        "Game": SimpleNamespace(GetModByName=lookup_mod, GetFormFromFile=lookup_form),
        "Self": self,
        "Parent": SimpleNamespace(OnConfigManagerReady=lambda *args: forwarded.append(args)),
        "a_eventName": "SKICP_configManagerReady",
        "a_strArg": "",
        "a_numArg": 0.0,
        "a_sender": object(),
    }
    exec(registration_guard(), environment)
    environment["guard"]()
    return calls, forwarded


class CoexistStatusProviderSourceTests(unittest.TestCase):
    def test_only_one_owned_quest_and_no_skyui_overrides_or_manager(self):
        files = sorted(PLUGIN.rglob("*.yaml"))
        self.assertEqual(len(files), 2)
        records = [path for path in files if path.name != "RecordData.yaml"]
        self.assertEqual(len(records), 1)
        source = records[0].read_text(encoding="utf-8")
        self.assertRegex(source, r"(?m)^FormKey: 000800:OpenMCM\.esp$")
        self.assertRegex(source, r"(?m)^EditorID: OpenMCM_ConfigMenuInstance$")
        self.assertNotIn("SKI_ConfigManager", source)
        self.assertNotIn("000802", source)
        self.assertNotIn("000820", source)
        self.assertNotIn("000830", source)
        self.assertEqual(re.findall(r"(?m)^FormKey: (.+)$", source), ["000800:OpenMCM.esp"])

    def test_companion_is_light_and_depends_on_real_skyui(self):
        header = (PLUGIN / "RecordData.yaml").read_text(encoding="utf-8")
        metadata = json.loads((PLUGIN / "spriggit-meta.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["ModKey"], "OpenMCM.esp")
        self.assertIn("ModKey: OpenMCM.esp", header)
        self.assertIn("- Small", header)
        self.assertEqual(re.findall(r"(?m)^  - Master: (.+)$", header), ["Skyrim.esm", "SkyUI_SE.esp"])

    def test_status_quest_uses_original_reload_alias_lifecycle(self):
        source = next((PLUGIN / "Quests").glob("*.yaml")).read_text(encoding="utf-8")
        for token in ("- StartGameEnabled", "- RunOnce", "- Name: OpenMCM_ConfigMenu",
                      "Data: OpenMCM", "- Status", "Object: 000800:OpenMCM.esp",
                      "Alias: 0", "- Name: SKI_PlayerLoadGameAlias", "NextAliasID: 1",
                      "- Name: PlayerAlias", "ForcedReference: 000014:Skyrim.esm"):
            self.assertIn(token, source)

    def test_provider_does_not_change_migration_version_or_parent_type(self):
        source = PROVIDER.read_text(encoding="utf-8")
        self.assertIn("Scriptname OpenMCM_ConfigMenu extends SKI_ConfigBase", source)
        self.assertRegex(source, r"Int Function GetVersion\(\)\s+Return 1\s+EndFunction")
        stub = (ROOT / "vendor/papyrus-stubs/Game.psc").read_text(encoding="utf-8")
        self.assertRegex(stub, r"(?im)^Int Function GetModByName\(String name\) Global Native$")


class CoexistStatusRegistrationTests(unittest.TestCase):
    def test_standalone_owner_registers_without_querying_absent_companion(self):
        owner = object()
        calls, forwarded = run_guard(owner, standalone=owner)
        self.assertEqual(calls, [("mod", "OpenMCM.esp"), ("form", 0x830, "SkyUI_SE.esp")])
        self.assertEqual(len(forwarded), 1)
        self.assertEqual(forwarded[0][:3], ("SKICP_configManagerReady", "", 0.0))

    def test_companion_owner_registers_for_full_and_light_load_indices(self):
        for index in (0, 8, 253, 254):
            with self.subTest(index=index):
                owner = object()
                calls, forwarded = run_guard(owner, companion_index=index, companion=owner)
                self.assertEqual(calls, [("mod", "OpenMCM.esp"), ("form", 0x800, "OpenMCM.esp")])
                self.assertEqual(len(forwarded), 1)

    def test_companion_prevents_old_standalone_provider_registering(self):
        old_owner, new_owner = object(), object()
        calls, forwarded = run_guard(old_owner, companion_index=254,
                                     companion=new_owner, standalone=old_owner)
        self.assertEqual(forwarded, [])
        self.assertNotIn(("form", 0x830, "SkyUI_SE.esp"), calls)

    def test_malformed_present_companion_fails_closed(self):
        owner = object()
        calls, forwarded = run_guard(owner, companion_index=254, standalone=owner)
        self.assertEqual(forwarded, [])
        self.assertNotIn(("form", 0x830, "SkyUI_SE.esp"), calls)

    def test_legacy_0x820_and_unrelated_instances_never_register(self):
        for index in (255, 254):
            with self.subTest(index=index):
                _, forwarded = run_guard(object(), companion_index=index,
                                         companion=object(), standalone=object())
                self.assertEqual(forwarded, [])

    def test_missing_standalone_owner_fails_closed(self):
        _, forwarded = run_guard(object())
        self.assertEqual(forwarded, [])


if __name__ == "__main__":
    unittest.main()
