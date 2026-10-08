"""Practical-example source contracts, not a Papyrus runtime emulator.

These checks inspect the actual teaching script and compile-only headers. The
package checker additionally validates the compiled PEX/quest/SEQ. Neither suite
substitutes for in-game checks of registration, save/load, input, or event timing.
"""
from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/field-guide/OpenMCM_FieldGuide.psc"


def strip_comments(source: str) -> str:
    """Keep semicolons within quoted strings while dropping Papyrus comments."""
    lines = []
    for line in source.splitlines():
        in_string = False
        escaped = False
        kept = []
        for char in line:
            if char == ";" and not in_string:
                break
            kept.append(char)
            if char == '"' and not escaped:
                in_string = not in_string
            escaped = char == "\\" and not escaped
        lines.append("".join(kept))
    return "\n".join(lines)


def body(source: str, name: str) -> str:
    match = re.search(
        rf"(?ims)^\s*(?:(?:Bool|Int|Float|String|Actor)(?:\[\])?\s+)?"
        rf"(Function|Event)\s+{re.escape(name)}\s*\([^)]*\)[^\n]*\n"
        rf"(.*?)^\s*End(?:Function|Event)\b", source)
    if match is None:
        raise AssertionError(f"missing Papyrus callback/function: {name}")
    return match.group(2)


class FieldGuideHeaderTests(unittest.TestCase):
    def header(self, name: str) -> str:
        return strip_comments((ROOT / "vendor/papyrus-stubs" / f"{name}.psc").read_text(encoding="utf-8"))

    def test_read_only_game_and_actor_signatures_match_installed_skse_sources(self):
        self.assertRegex(self.header("Game"), r"(?im)^Actor Function GetPlayer\(\) Global Native$")
        self.assertRegex(self.header("Actor"), r"(?im)^Scriptname Actor extends ObjectReference Hidden$")
        self.assertRegex(self.header("Actor"), r"(?im)^Float Function GetActorValue\(String asValueName\) Native$")
        self.assertRegex(self.header("ObjectReference"), r"(?im)^Scriptname ObjectReference extends Form Hidden$")

    def test_hotkey_and_menu_guard_signatures_match_installed_skse_sources(self):
        self.assertRegex(self.header("Utility"), r"(?im)^Bool Function IsInMenuMode\(\) Global Native$")
        self.assertRegex(self.header("Form"), r"(?im)^Function RegisterForKey\(Int keyCode\) Native$")
        self.assertRegex(self.header("Form"), r"(?im)^Function UnregisterForAllKeys\(\) Native$")
        self.assertRegex(self.header("Form"), r"(?im)^Event OnKeyDown\(Int keyCode\)$")


class FieldGuideSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.code = strip_comments(cls.source)

    def test_uses_opt_in_base_and_three_practical_pages(self):
        self.assertRegex(self.code, r"(?im)^Scriptname OpenMCM_FieldGuide extends OpenMCM_ConfigBase$")
        init = body(self.code, "OnConfigInit")
        self.assertIn("New String[3]", init)
        for index, name in enumerate(("Overview", "Checklist", "Preferences")):
            self.assertIn(f'Pages[{index}] = "{name}"', init)

    def test_demonstrates_every_existing_skyui_control_using_named_api(self):
        for name in ("Header", "Text", "Toggle", "Slider", "Menu", "Color", "KeyMap", "Input"):
            with self.subTest(control=name):
                self.assertIn(f"AddNamed{name}(", self.code)

    def test_reads_real_carry_values_and_never_changes_player_gameplay(self):
        self.assertIn("Game.GetPlayer()", self.code)
        self.assertIn('GetActorValue("InventoryWeight")', self.code)
        self.assertIn('GetActorValue("CarryWeight")', self.code)
        forbidden = ("SetActorValue", "ForceActorValue", "ModActorValue", "DamageActorValue",
                     "RestoreActorValue", "AddItem", "RemoveItem", "EquipItem", "UnequipItem",
                     "MoveTo", "SetPosition", "SetScale", "SetStage", "EnablePlayerControls",
                     "DisablePlayerControls", "SaveGame", "LoadGame", "ExecuteConsoleCommand")
        for method in forbidden:
            with self.subTest(method=method):
                self.assertNotRegex(self.code, rf"(?i)\b{method}\s*\(")

    def test_has_no_polling_or_update_registration(self):
        self.assertNotRegex(self.code, r"(?i)\bRegisterFor(?:Single)?Update(?:GameTime)?\s*\(")
        self.assertNotRegex(self.code, r"(?im)^\s*Event\s+OnUpdate(?:GameTime)?\s*\(")

    def test_example_does_not_override_or_short_circuit_sdk_bridge(self):
        for internal in ("OnInit", "SetPage", "OpenConfig", "CloseConfig", "OpenMCM_ClearPage",
                         "OpenMCM_SendText", "SelectOption", "HighlightOption", "AddOption"):
            self.assertNotRegex(self.code, rf"(?im)^\s*(?:(?:Int|Bool)\s+)?(?:Event|Function)\s+{internal}\s*\(")
        self.assertIn("Parent.OnGameReload()", body(self.code, "OnGameReload"))

    def test_page_build_does_not_try_to_capture_ready_token_or_navigate(self):
        page = body(self.code, "OnPageReset")
        self.assertNotIn("GetPageToken(", page)
        self.assertNotIn("SetCurrentPage(", page)

    def test_live_text_and_navigation_are_demonstrated_without_raw_ui_writes(self):
        for method in ("SetOptionLabel", "SetOptionText", "SetOptionHelp", "SetLiveInfoText",
                       "SetCurrentPage", "SetOptionsEnabled"):
            self.assertIn(method + "(", self.code)
        self.assertNotRegex(self.code, r"(?i)\bUI\.(?:Invoke|Set)\w*\s*\(")

    def test_delayed_worker_never_reacquires_token_or_resets_a_new_page(self):
        worker = body(self.code, "OnDelayedRefresh")
        self.assertIn("a_sender != Self", worker)
        self.assertGreaterEqual(worker.count("job != refreshGeneration"), 2)
        self.assertLess(worker.index("Int token = pendingPageToken"), worker.index("Utility.WaitMenuMode"))
        self.assertNotIn("GetPageToken()", worker)
        self.assertNotIn("ForcePageReset()", worker)
        self.assertIn("PaintSummary(token, False)", worker)
        paint = body(self.code, "PaintSummary")
        self.assertRegex(paint, r"If a_allowReset\s+ForcePageReset\(\)")

    def test_close_reload_and_disable_cancel_the_pending_generation(self):
        self.assertIn("CancelPendingRefresh()", body(self.code, "OnConfigClose"))
        self.assertIn("CancelPendingRefresh()", body(self.code, "OnGameReload"))
        cancel = body(self.code, "CancelPendingRefresh")
        self.assertIn("refreshPending = False", cancel)
        self.assertIn("pendingPageToken = 0", cancel)
        self.assertIn("refreshGeneration += 1", cancel)
        self.assertIn("refreshGeneration as Float", body(self.code, "QueueRefresh"))

    def test_input_is_bounded_raw_in_dialog_and_escaped_for_display(self):
        self.assertIn("StringUtil.Substring(a_input, 0, 40)", body(self.code, "OnOptionInputAccept"))
        self.assertIn("SetInputDialogStartText(tripName)", body(self.code, "OnOptionInputOpen"))
        self.assertIn("SetInputOptionValue(a_option, EscapeLabelText(tripName))", body(self.code, "OnOptionInputAccept"))
        for entity in ("&amp;", "&lt;", "&gt;"):
            self.assertIn(entity, body(self.code, "EscapeLabelText"))

    def test_hotkey_defaults_unbound_rebinds_and_ignores_menus(self):
        self.assertRegex(self.code, r"Int summaryKey = -1")
        bind = body(self.code, "RebindSummaryKey")
        self.assertLess(bind.index("UnregisterForAllKeys"), bind.index("RegisterForKey"))
        self.assertIn("guideEnabled && summaryKey >= 1 && summaryKey <= 255", bind)
        self.assertIn("!Utility.IsInMenuMode()", body(self.code, "OnKeyDown"))
        change = body(self.code, "OnOptionKeyMapChange")
        self.assertLess(change.index("If !ShowMessage"), change.index("summaryKey = a_keyCode"))

    def test_api_off_fallback_and_groups_rebuild_the_same_saved_condition(self):
        self.assertIn("!OpenMCM.IsAPIEnabled()", body(self.code, "OnPageReset"))
        self.assertIn("!guideEnabled", body(self.code, "FeatureFlags"))
        self.assertIn("!guideEnabled || !OpenMCM.IsAPIEnabled()", body(self.code, "DelayedFlags"))
        self.assertIn("SetOptionsEnabled(keys, guideEnabled, a_token)", body(self.code, "RefreshEnabledGroup"))
        self.assertIn("ForcePageReset()", body(self.code, "RefreshEnabledGroup"))
        self.assertIn("SetInfoText(", body(self.code, "OnOptionHighlight"))


if __name__ == "__main__":
    unittest.main()
