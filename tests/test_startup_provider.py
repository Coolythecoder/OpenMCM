from __future__ import annotations

import re
import struct
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_SOURCE = REPOSITORY_ROOT / "src" / "papyrus" / "OpenMCM_ConfigMenu.psc"
PROVIDER_RECORD = (
    REPOSITORY_ROOT
    / "src"
    / "plugin"
    / "SkyUI_SE.esp"
    / "Quests"
    / "OpenMCM_ConfigMenuInstance - 000830_SkyUI_SE.esp.yaml"
)
TOMBSTONE_RECORD = (
    REPOSITORY_ROOT
    / "src"
    / "plugin"
    / "SkyUI_SE.esp"
    / "Quests"
    / "SKI_ConfigMenuInstance - 000820_SkyUI_SE.esp.yaml"
)
BUILD_SCRIPT = REPOSITORY_ROOT / "scripts" / "Build-OpenMCM.ps1"


class StartupProviderTests(unittest.TestCase):
    def test_builtin_provider_uses_the_same_quest_lifecycle_as_skyui(self) -> None:
        record = PROVIDER_RECORD.read_text(encoding="utf-8")
        self.assertRegex(record, r"(?m)^FormKey: 000830:SkyUI_SE\.esp$")
        self.assertRegex(record, r"(?m)^EditorID: OpenMCM_ConfigMenuInstance$")
        self.assertRegex(record, r"(?m)^\s*- Name: OpenMCM_ConfigMenu$")
        self.assertIn("- StartGameEnabled", record)
        self.assertIn("- RunOnce", record)
        self.assertIn("- Name: SKI_PlayerLoadGameAlias", record)
        self.assertIn("ForcedReference: 000014:Skyrim.esm", record)

    def test_builtin_provider_is_a_real_config_base_menu(self) -> None:
        source = PROVIDER_SOURCE.read_text(encoding="utf-8")
        self.assertRegex(
            source,
            r"(?im)^Scriptname\s+OpenMCM_ConfigMenu\s+extends\s+SKI_ConfigBase$",
        )
        self.assertIn('ModName = "OpenMCM"', source)
        self.assertIn('Pages[0] = "Status"', source)
        self.assertIn('AddTextOption("MCM host", "Online")', source)
        self.assertIn('Game.GetFormFromFile(0x000830, "SkyUI_SE.esp") != Self', source)
        self.assertIn("Parent.OnConfigManagerReady", source)

    def test_skyui_builtin_form_is_an_inactive_migration_tombstone(self) -> None:
        record = TOMBSTONE_RECORD.read_text(encoding="utf-8")
        self.assertRegex(record, r"(?m)^FormKey: 000820:SkyUI_SE\.esp$")
        self.assertRegex(record, r"(?m)^EditorID: SKI_ConfigMenuInstance$")
        self.assertNotIn("VirtualMachineAdapter", record)
        self.assertNotIn("StartGameEnabled", record)

    def test_sequence_contains_manager_and_builtin_provider_form_ids(self) -> None:
        script = BUILD_SCRIPT.read_text(encoding="utf-8")
        byte_literals = re.search(
            r"\$sequenceBytes\s*=\s*\[byte\[\]\]@\((.*?)\)",
            script,
            re.DOTALL,
        )
        self.assertIsNotNone(byte_literals)
        values = [
            int(token, 16)
            for token in re.findall(r"0x([0-9A-Fa-f]{2})", byte_literals.group(1))
        ]
        self.assertEqual(bytes(values), struct.pack("<II", 0x01000802, 0x01000830))
        self.assertIn("'Seq'", script)
        self.assertIn("'SkyUI_SE.seq'", script)


if __name__ == "__main__":
    unittest.main()
