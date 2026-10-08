"""Source contracts for the save-local MCM browser bridge.

These checks protect the unchanged SkyUI/MCM Helper registry ABI and the
Papyrus event boundary; they do not execute the Skyrim VM. Browser parsing,
sorting and rendering have separate actual-AS2 tests.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _code(source: str) -> str:
    return re.sub(r'("[^"\r\n]*")|;[^\r\n]*', lambda match: match.group(1) or "", source)


def _body(source: str, kind: str, name: str) -> str:
    match = re.search(
        rf"(?ims)^\s*(?:\w+\s+)?{kind}\s+{re.escape(name)}\s*\([^)]*\)"
        rf"(.*?)^\s*End{kind}\b", _code(source))
    if match is None:
        raise AssertionError(f"missing {kind} {name}")
    return match.group(1)


class BrowserRegistryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manager = (ROOT / "src/papyrus/SKI_ConfigManager.psc").read_text(encoding="utf-8")
        cls.code = _code(cls.manager)

    def test_new_saved_field_is_appended_with_empty_migration_default(self) -> None:
        fields = self.code.split("Int Function GetVersion", 1)[0]
        self.assertRegex(fields, r'(?m)^String _openmcmBrowserState = ""\s*$')
        self.assertGreater(fields.index("String _openmcmBrowserState"),
                           fields.index("Bool _openmcmAPIEnabled"))

    def test_browser_preferences_never_replace_legacy_registry_types(self) -> None:
        self.assertRegex(self.code, r"(?m)^SKI_ConfigBase\[\] _modConfigs\s*$")
        self.assertRegex(self.code, r"(?m)^String\[\] _modNames\s*$")
        self.assertRegex(self.code, r"(?m)^SKI_ConfigBase _activeConfig\s*$")
        self.assertIn("_modConfigs = New SKI_ConfigBase[128]", _body(self.manager, "Event", "OnInit"))
        self.assertIn("_modNames = New String[128]", _body(self.manager, "Event", "OnInit"))
        self.assertEqual(_body(self.manager, "Function", "GetVersion").strip(), "Return 4")
        self.assertNotIn("MCMR_Native", self.code)
        self.assertNotIn("OpenMCMBrowserNative", self.code)

    def test_reload_registers_browser_event_without_erasing_saved_preferences(self) -> None:
        reload_body = _body(self.manager, "Event", "OnGameReload")
        self.assertIn('RegisterForModEvent("OPENMCM_browserStateChanged", "OnBrowserStateChanged")', reload_body)
        self.assertNotRegex(reload_body, r"_openmcmBrowserState\s*=")

    def test_registry_reset_repair_and_slot_reuse_do_not_touch_name_keyed_preferences(self) -> None:
        for name in ("RegisterMod", "UnregisterMod", "ForceReset", "OpenMCM_TryForceReset", "CleanUp", "InitializeStorage"):
            with self.subTest(name=name):
                body = _body(self.manager, "Function", name)
                self.assertNotIn("_openmcmBrowserState", body)
                self.assertNotIn("loadBrowserState", body)

    def test_state_update_validates_before_replacing_last_snapshot(self) -> None:
        body = _body(self.manager, "Event", "OnBrowserStateChanged")
        self.assertRegex(body, r"(?s)If !IsValidBrowserState\(a_strArg\)\s+Return\s+EndIf")
        self.assertLess(body.index("IsValidBrowserState(a_strArg)"), body.index("_openmcmBrowserState = a_strArg"))
        self.assertEqual(body.count("_openmcmBrowserState ="), 1)
        self.assertNotIn("_modConfigs", body)
        self.assertNotIn("_modNames", body)
        self.assertNotIn("a_numArg", body)

    def test_empty_oversized_and_unknown_version_payloads_are_rejected(self) -> None:
        body = _body(self.manager, "Function", "IsValidBrowserState")
        self.assertIn("Int stateLength = StringUtil.GetLength(a_state)", body)
        self.assertRegex(body, r"(?s)If stateLength < 10 \|\| stateLength > 32768\s+Return False\s+EndIf")
        self.assertIn('Return StringUtil.Substring(a_state, 0, 10) == "OPENMCMB1|"', body)

    def test_final_edit_event_can_finish_after_movie_closes_without_touching_ui(self) -> None:
        body = _body(self.manager, "Event", "OnBrowserStateChanged")
        self.assertNotIn("UI.", body)
        self.assertNotIn("_menuOpen", body)
        self.assertNotIn("RegisterForSingleUpdate", body)
        self.assertNotIn("PublishModList", body)

    def test_only_validated_event_replaces_saved_browser_state(self) -> None:
        assignments = re.findall(r"(?im)^\s*(?:String\s+)?_openmcmBrowserState\s*=\s*([^\r\n]+)", self.code)
        self.assertEqual(assignments, ['""', "a_strArg"])

    def test_mod_list_handshake_loads_browser_state_before_rendering_names(self) -> None:
        body = _body(self.manager, "Function", "PublishModList")
        self.assertLess(body.index("PublishOpenMCMAPIState()"), body.index("PublishBrowserState()"))
        self.assertLess(body.index("PublishBrowserState()"), body.index('".setModNames"'))
        self.assertIn('UI.InvokeStringA(JOURNAL_MENU, MENU_ROOT + ".setModNames", _modNames)', body)

    def test_browser_publication_does_not_invoke_a_closed_journal(self) -> None:
        body = _body(self.manager, "Function", "PublishBrowserState")
        self.assertRegex(body, r"(?s)If !UI\.IsMenuOpen\(JOURNAL_MENU\)\s+Return\s+EndIf")
        self.assertLess(body.index("UI.IsMenuOpen"), body.index("UI.InvokeString"))
        self.assertIn('UI.InvokeString(JOURNAL_MENU, MENU_ROOT + ".loadBrowserState", _openmcmBrowserState)', body)

    def test_close_does_not_call_destroyed_movie_to_save_preferences(self) -> None:
        body = _body(self.manager, "Event", "OnMenuClose")
        self.assertNotIn("flushBrowserState", body)
        self.assertNotIn("UI.", body)

    def test_heartbeat_does_not_poll_browser_state(self) -> None:
        body = _body(self.manager, "Event", "OnUpdate")
        self.assertNotIn("Browser", body)
        self.assertNotIn("UI.", body)

    def test_string_helpers_are_only_native_skse_compile_declarations(self) -> None:
        stub = _code((ROOT / "vendor/papyrus-stubs/StringUtil.psc").read_text(encoding="utf-8"))
        self.assertRegex(stub, r"(?im)^Int Function GetLength\(String s\) Global Native\s*$")
        self.assertRegex(stub, r"(?im)^String Function Substring\(String s, Int startIndex, Int len = 0\) Global Native\s*$")
        self.assertFalse((ROOT / "src/papyrus/StringUtil.psc").exists())


if __name__ == "__main__":
    unittest.main()
