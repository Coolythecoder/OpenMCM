"""SDK source contracts and a lifecycle model; not a Papyrus runtime emulator.

The model asserts intended invariants. Compiled-provider and AVM1 tests are still
needed to verify actual inheritance, event dispatch, rendering and input.
"""
from __future__ import annotations

import re
import unittest
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PATH = ROOT / "src/papyrus/SKI_ConfigBase.psc"
SDK_PATH = ROOT / "src/papyrus/OpenMCM_ConfigBase.psc"


def _body(source: str, name: str) -> str:
    pattern = rf"(?ims)^\s*(?:(?:int|bool|string|float)\s+)?function\s+{re.escape(name)}\s*\([^)]*\)(.*?)^\s*endfunction\b"
    match = re.search(pattern, source)
    if match is None:
        raise AssertionError(f"missing Papyrus function {name}")
    return match.group(1)


@dataclass
class _UIContextModel:
    """Model only: one atomic endpoint checks the currently displayed page."""
    provider: int = 3
    page: int = 0
    token: int = 1
    active: bool = True
    mode: str = "pages"
    writes: list[tuple] = field(default_factory=list)

    def accepts(self, provider: int, page: int, token: int) -> bool:
        return (self.active and self.mode == "pages" and token > 0
                and token == self.token and provider == self.provider and page == self.page)

    def update(self, provider: int, page: int, token: int, operation: str, *args) -> bool:
        if not self.accepts(provider, page, token):
            return False
        self.writes.append((operation, *args))
        return True


@dataclass
class _SDKLifecycleModel:
    """Model only: does not interpret or execute the Papyrus implementation."""
    ui: _UIContextModel
    provider: int = 3
    page: int = 0
    page_number: int = 1
    generation: int = 1
    token: int = 0
    host_token: int = 0
    slots: dict[int, tuple[int, int]] = field(default_factory=dict)
    names: dict[str, int] = field(default_factory=dict)
    help: dict[int, str] = field(default_factory=dict)

    def invalidate(self) -> None:
        self.generation = min(self.generation + 1, 2147483647)
        self.token = 0
        self.host_token = 0
        self.slots.clear()
        self.names.clear()
        self.help.clear()

    def capture(self) -> bool:
        candidate = self.ui.token
        accepted = self.generation < 2147483647 and self.ui.accepts(self.provider, self.page, candidate)
        self.host_token = candidate if accepted else 0
        self.token = self.generation if accepted else 0
        return self.token > 0

    def add_option(self, option_id: int, option_type: int) -> bool:
        if option_id < 0:
            return False
        index = option_id % 256
        if index >= 128 or option_id // 256 != self.page_number:
            return False
        for key in [key for key, slot in self.names.items() if slot == index]:
            del self.names[key]
        self.help.pop(index, None)
        self.slots[index] = (option_id, option_type)
        return True

    def bind(self, key: str, option_id: int, help_text: str = "") -> bool:
        key = key.lower()  # Papyrus String comparisons/Find are case-insensitive.
        if not key or key in self.names or option_id < 0:
            return False
        index = option_id % 256
        slot = self.slots.get(index)
        if slot is None or slot[0] != option_id or slot[1] == 0 or index in self.names.values():
            return False
        self.names[key] = index
        self.help[index] = help_text
        return True

    def option_id(self, key: str) -> int:
        index = self.names.get(key.lower())
        return -1 if index is None else self.slots[index][0]

    def valid(self, captured_token: int) -> bool:
        return self.token > 0 and captured_token == self.token and self.ui.accepts(
            self.provider, self.page, self.host_token)

    def update(self, key: str, value: str, captured_token: int) -> bool:
        if not self.valid(captured_token) or self.option_id(key) < 0:
            return False
        return self.ui.update(self.provider, self.page, self.host_token,
                              "label", self.option_id(key), value)

    def highlight(self, index: int, callback) -> bool:
        captured_token = self.token
        text = self.help.get(index, "")
        replacement = callback(text)
        # None means no SetInfoText call; an empty string explicitly clears help.
        if replacement is not None:
            text = replacement
        if not self.valid(captured_token):
            return False
        return self.ui.update(self.provider, self.page, self.host_token, "help", index, text)


class OpenMCMAPILifecycleModelTests(unittest.TestCase):
    """These model tests must not be described as an in-game verification."""
    def setUp(self) -> None:
        self.ui = _UIContextModel()
        self.sdk = _SDKLifecycleModel(self.ui)
        self.assertTrue(self.sdk.add_option(256, 2))
        self.assertTrue(self.sdk.bind("status", 256, "Automatic help"))
        self.assertTrue(self.sdk.capture())

    def test_named_reference_keeps_full_page_id_and_case_insensitive_key(self):
        self.assertEqual(self.sdk.option_id("STATUS"), 256)
        self.assertEqual(self.sdk.option_id("missing"), -1)

    def test_stale_full_id_cannot_bind_same_physical_slot(self):
        self.assertFalse(self.sdk.bind("stale", 512))

    def test_duplicate_or_empty_key_does_not_replace_binding(self):
        self.assertTrue(self.sdk.add_option(257, 3))
        snapshot = dict(self.sdk.names)
        for key, option in (("", 257), ("status", 257), ("STATUS", 257), ("alias", 256)):
            with self.subTest(key=key, option=option):
                self.assertFalse(self.sdk.bind(key, option))
                self.assertEqual(self.sdk.names, snapshot)

    def test_failed_add_and_out_of_range_slots_cannot_bind(self):
        for option in (-1, 384, 511, 512):
            with self.subTest(option=option):
                self.assertFalse(self.sdk.add_option(option, 2))
                self.assertFalse(self.sdk.bind("bad", option))

    def test_last_valid_slot_retains_full_id(self):
        self.assertTrue(self.sdk.add_option(383, 2))
        self.assertTrue(self.sdk.bind("last", 383))
        self.assertEqual(self.sdk.option_id("last"), 383)

    def test_cursor_overwrite_removes_name_and_help(self):
        self.assertTrue(self.sdk.add_option(256, 3))
        self.assertEqual(self.sdk.option_id("status"), -1)
        self.assertNotIn(0, self.sdk.help)
        self.assertFalse(self.sdk.update("status", "old", 1))

    def test_same_page_rebuild_rejects_old_token_even_with_same_option_id(self):
        old_token = self.sdk.token
        self.sdk.invalidate()
        self.ui.token += 1
        self.sdk.add_option(256, 2)
        self.sdk.bind("status", 256)
        self.sdk.capture()
        self.assertEqual(self.sdk.option_id("status"), 256)
        self.assertFalse(self.sdk.update("status", "stale", old_token))
        self.assertTrue(self.sdk.update("status", "current", self.sdk.token))
        self.assertEqual(self.ui.writes, [("label", 256, "current")])

    def test_new_journal_movie_reusing_host_token_does_not_revalidate_old_public_token(self):
        old_token = self.sdk.token
        self.sdk.invalidate()
        # A newly constructed SWF may restart its own counter at one.
        self.ui = _UIContextModel(token=1)
        self.sdk.ui = self.ui
        self.sdk.add_option(256, 2)
        self.sdk.bind("status", 256)
        self.assertTrue(self.sdk.capture())
        self.assertEqual(self.sdk.host_token, 1)
        self.assertGreater(self.sdk.token, old_token)
        self.assertFalse(self.sdk.update("status", "old callback", old_token))
        self.assertTrue(self.sdk.update("status", "new callback", self.sdk.token))
        self.assertEqual(self.ui.writes, [("label", 256, "new callback")])

    def test_exhausted_public_generation_fails_closed_without_wrapping(self):
        self.sdk.generation = 2147483646
        self.sdk.invalidate()
        self.assertEqual(self.sdk.generation, 2147483647)
        self.assertFalse(self.sdk.capture())
        self.sdk.invalidate()
        self.assertEqual(self.sdk.generation, 2147483647)
        self.assertFalse(self.sdk.capture())

    def test_provider_switch_rejects_previous_provider(self):
        self.ui.provider = 4
        self.assertFalse(self.sdk.update("status", "stale", self.sdk.token))
        self.assertEqual(self.ui.writes, [])

    def test_original_page_index_must_match(self):
        self.ui.page = 1
        self.assertFalse(self.sdk.update("status", "stale", self.sdk.token))

    def test_back_navigation_rejects_updates_even_if_papyrus_remains_open(self):
        self.ui.mode = "mods"
        self.assertGreater(self.sdk.token, 0)
        self.assertFalse(self.sdk.update("status", "stale", self.sdk.token))

    def test_closed_ui_rejects_updates(self):
        self.ui.active = False
        self.assertFalse(self.sdk.update("status", "stale", self.sdk.token))

    def test_close_reload_or_reset_clear_all_metadata(self):
        self.sdk.invalidate()
        self.assertEqual((self.sdk.token, self.sdk.names, self.sdk.slots, self.sdk.help),
                         (0, {}, {}, {}))
        self.assertFalse(self.sdk.update("status", "stale", 1))

    def test_failed_capture_does_not_leave_previous_valid_token(self):
        self.ui.provider = 4
        self.assertFalse(self.sdk.capture())
        self.assertEqual(self.sdk.token, 0)

    def test_zero_token_is_never_a_capability(self):
        self.assertFalse(self.sdk.update("status", "stale", 0))
        self.ui.token = 0
        self.assertFalse(self.sdk.capture())

    def test_default_help_is_used_when_callback_does_not_override(self):
        self.assertTrue(self.sdk.highlight(0, lambda default: None))
        self.assertEqual(self.ui.writes, [("help", 0, "Automatic help")])

    def test_callback_can_override_or_explicitly_clear_default_help(self):
        for replacement in ("Authored override", ""):
            with self.subTest(replacement=replacement):
                self.assertTrue(self.sdk.highlight(0, lambda default: replacement))
                self.assertEqual(self.ui.writes[-1], ("help", 0, replacement))

    def test_page_change_inside_highlight_callback_rejects_old_help(self):
        def rebuild(default):
            self.sdk.invalidate()
            self.ui.token += 1
            self.sdk.add_option(256, 2)
            self.sdk.bind("status", 256, "Replacement help")
            self.sdk.capture()
            return "Late help from old callback"
        self.assertFalse(self.sdk.highlight(0, rebuild))
        self.assertEqual(self.ui.writes, [])

    def test_endpoint_rechecks_context_after_initial_caller_validation(self):
        captured = self.sdk.token
        self.assertTrue(self.sdk.valid(captured))
        self.ui.token += 1
        self.assertFalse(self.ui.update(3, 0, captured, "label", 256, "stale"))
        self.assertEqual(self.ui.writes, [])

    def test_formatted_text_is_transmitted_without_stripping_author_markup(self):
        text = '<font color="#AADD22">$OPENMCM_Status</font>'
        self.assertTrue(self.sdk.update("status", text, self.sdk.token))
        self.assertEqual(self.ui.writes[-1], ("label", 256, text))

    def test_empty_slot_cannot_bind_but_header_can(self):
        self.assertTrue(self.sdk.add_option(257, 0))
        self.assertFalse(self.sdk.bind("empty", 257))
        self.assertTrue(self.sdk.add_option(258, 1))
        self.assertTrue(self.sdk.bind("heading", 258))


class OpenMCMAPISourceContractTests(unittest.TestCase):
    """Actual-source checks complement, but do not turn the model into a VM."""
    @classmethod
    def setUpClass(cls):
        cls.base = BASE_PATH.read_text(encoding="utf-8")
        cls.sdk = SDK_PATH.read_text(encoding="utf-8")
        cls.api = (ROOT / "src/papyrus/OpenMCM.psc").read_text(encoding="utf-8")

    def test_opt_in_inheritance_and_independent_api_version(self):
        self.assertRegex(self.sdk, r"(?im)^Scriptname OpenMCM_ConfigBase extends SKI_ConfigBase\b")
        self.assertRegex(_body(self.api, "GetAPIVersion"), r"(?im)^\s*Return 1\s*$")
        self.assertNotRegex(self.sdk, r"(?im)^\s*Int Function GetVersion\(")
        self.assertNotIn("Return 4", _body(self.api, "GetHostAPIVersion"))
        self.assertIn("UI.GetInt", _body(self.api, "GetHostAPIVersion"))

    def test_capabilities_are_explicit_and_do_not_claim_unimplemented_features(self):
        body = _body(self.api, "HasCapability")
        capabilities = set(re.findall(r'a_capability\s*==\s*"([^"]+)"', body))
        self.assertEqual(capabilities, {"named_options", "automatic_help", "live_text", "page_tokens",
                                       "page_navigation", "conditional_groups"})
        self.assertNotRegex(body, r"(?im)^\s*Return True\b")

    def test_new_saved_fields_do_not_shadow_skyui_helper_fields(self):
        preamble = self.sdk.split("Event OnGameReload", 1)[0]
        fields = re.findall(r"(?im)^\s*(?:String|Int|Float|Bool)(?:\[\])?\s+(_\w+)", preamble)
        self.assertGreater(len(fields), 0)
        self.assertTrue(all(name.startswith("_openmcm") for name in fields), fields)

    def test_base_fallbacks_retain_unextended_help_behavior(self):
        self.assertRegex(_body(self.base, "OpenMCM_CapturePageToken"), r"Return 0\b")
        self.assertIn('Return ""', _body(self.base, "OpenMCM_DefaultHelp"))
        self.assertIn('UI.InvokeString(JOURNAL_MENU, MENU_ROOT + ".setInfoText", a_text)',
                      _body(self.base, "OpenMCM_PublishHelp"))
        self.assertIn("Return _configID", _body(self.base, "OpenMCM_GetConfigID"))

    def test_help_token_and_default_precede_both_callbacks_then_publish(self):
        body = _body(self.base, "HighlightOption")
        capture = body.index("OpenMCM_CapturePageToken()")
        default = body.index("_infoText = OpenMCM_DefaultHelp(a_index)")
        normal = body.index("OnOptionHighlight(a_index + (_currentPageNum * 0x100))")
        enter_state = body.index("GotoState(optionState)")
        state = body.index("OnHighlightST()")
        restore_state = body.index("GotoState(previousState)")
        publish = body.index("OpenMCM_PublishHelp(a_index, _infoText, openmcmToken)")
        self.assertLess(capture, default)
        self.assertLess(default, normal)
        self.assertLess(default, enter_state)
        self.assertLess(enter_state, state)
        self.assertLess(state, restore_state)
        self.assertLess(restore_state, publish)
        self.assertLess(normal, publish)
        self.assertNotIn('_infoText == ""', body)

    def test_reset_close_and_reload_invalidate_before_parent_callbacks(self):
        for name in ("SetPage", "CloseConfig"):
            with self.subTest(name=name):
                body = _body(self.sdk, name)
                self.assertLess(body.index("OpenMCM_ClearPage()"), body.index("Parent." + name))
        for name in ("OnGameReload", "OnConfigManagerReset"):
            with self.subTest(name=name):
                body = re.search(rf"(?ims)^Event {name}\([^)]*\)(.*?)^EndEvent", self.sdk).group(1)
                self.assertLess(body.index("OpenMCM_ClearPage()"), body.index("Parent." + name))

    def test_page_token_capture_happens_after_parent_flush_and_checks_identity(self):
        body = _body(self.sdk, "SetPage")
        self.assertLess(body.index("Parent.SetPage(a_page, a_index)"),
                        body.index('_openmcmHostToken = UI.GetInt'))
        self.assertIn('.openMCMProviderID', body)
        self.assertIn('.openMCMPageIndex', body)
        self.assertIn('== a_index', body)
        self.assertIn("_openmcmPageToken = _openmcmGeneration", body)
        self.assertNotIn("_openmcmPageToken = UI.GetInt", body)

    def test_invalidation_releases_all_named_metadata_and_capability(self):
        body = _body(self.sdk, "OpenMCM_ClearPage")
        self.assertIn("_openmcmPageToken = 0", body)
        self.assertIn("_openmcmHostToken = 0", body)
        self.assertIn("_openmcmProviderID = -1", body)
        for field in ("Keys", "Help", "IDs", "Types"):
            self.assertRegex(body, rf"_openmcm{field}\s*=\s*New (?:String|Int)\[1\]")

    def test_public_generation_never_resets_to_reused_movie_counter(self):
        body = _body(self.sdk, "OpenMCM_ClearPage")
        self.assertIn("_openmcmGeneration += 1", body)
        self.assertIn("If _openmcmGeneration < 2147483647", body)
        self.assertNotRegex(body, r"_openmcmGeneration\s*=\s*0\b")
        self.assertIn("_openmcmGeneration < 2147483647", _body(self.sdk, "SetPage"))

    def test_option_add_tracks_full_id_and_clears_previous_name_help(self):
        body = _body(self.sdk, "AddOption")
        self.assertIn("Parent.AddOption(", body)
        self.assertIn("optionID >= 0 && _openmcmBuilding", body)
        self.assertIn('_openmcmKeys[index] = ""', body)
        self.assertIn('_openmcmHelp[index] = ""', body)
        self.assertIn('_openmcmIDs[index] = optionID', body)
        self.assertIn('_openmcmTypes[index] = a_optionType', body)

    def test_opt_in_slot_overwrite_clears_old_st_callback_mapping(self):
        body = _body(self.sdk, "AddOption")
        self.assertIn("OpenMCM_ClearOptionState(optionID)", body)
        clear = _body(self.base, "OpenMCM_ClearOptionState")
        self.assertIn("(a_option / 0x100) == _currentPageNum", clear)
        self.assertIn("IsValidPageIndex(index)", clear)
        self.assertIn('_stateOptionMap[index] = ""', clear)
        self.assertNotIn("OpenMCM_ClearOptionState", _body(self.base, "AddOption"))
        # ST addition assigns its requested state after dynamic AddOption returns.
        state_add = _body(self.base, "AddOptionST")
        self.assertLess(state_add.index("AddOption("), state_add.index("_stateOptionMap[index] = a_stateName"))

    def test_bad_name_is_rejected_before_add_consumes_cursor(self):
        body = _body(self.sdk, "OpenMCM_AddNamed")
        self.assertLess(body.index("!OpenMCM_CanBind(a_key)"), body.index("AddOption("))
        validation = _body(self.sdk, "OpenMCM_CanBind")
        self.assertIn("!_openmcmBuilding", validation)
        self.assertIn('a_key == ""', validation)
        self.assertIn("_openmcmKeys.Find(a_key)", validation)
        self.assertIn('_openmcmKeys[index] != ""', _body(self.sdk, "BindOption"))

    def test_binding_resolves_full_id_type_and_physical_slot(self):
        body = _body(self.sdk, "OpenMCM_ResolveID")
        self.assertIn("(a_option / 0x100) != (_openmcmPageIndex + 1)", body)
        self.assertIn("index >= 128", body)
        self.assertIn("_openmcmIDs[index] != a_option", body)
        self.assertIn("_openmcmTypes[index] == OPTION_TYPE_EMPTY", body)

    def test_state_binding_uses_existing_state_lookup_and_preserves_full_id(self):
        body = _body(self.sdk, "BindStateOption")
        self.assertIn("GetStateOptionIndex(a_stateName)", body)
        self.assertIn("index + ((_openmcmPageIndex + 1) * 0x100)", body)
        self.assertNotIn("GotoState", body)

    def test_convenience_additions_keep_standard_option_types(self):
        for name, kind in (("Header", "HEADER"), ("Text", "TEXT"), ("Toggle", "TOGGLE"),
                           ("Slider", "SLIDER"), ("Menu", "MENU"), ("Color", "COLOR"),
                           ("KeyMap", "KEYMAP"), ("Input", "INPUT")):
            with self.subTest(name=name):
                self.assertIn(f"OpenMCM_AddNamed(a_key, OPTION_TYPE_{kind},", _body(self.sdk, "AddNamed" + name))

    def test_live_updates_use_one_guarded_payload_not_legacy_option_cursor(self):
        for name in ("SetOptionLabel", "SetOptionText", "SetOptionHelp"):
            with self.subTest(name=name):
                body = _body(self.sdk, name)
                self.assertLess(body.index("OpenMCM_ResolveUpdate(a_key, a_token)"), body.index("OpenMCM_SendText("))
        for name, guard in (("SetLiveInfoText", "IsPageTokenValid"),
                            ("OpenMCM_PublishHelp", "OpenMCM_IsPageContextValid")):
            with self.subTest(name=name):
                body = _body(self.sdk, name)
                self.assertLess(body.index(guard + "(a_token)"), body.index("OpenMCM_SendText("))
        body = _body(self.sdk, "OpenMCM_SendText")
        self.assertEqual(body.count("UI.InvokeStringA("), 1)
        self.assertLess(body.index("a_token != _openmcmPageToken"), body.index("UI.InvokeStringA("))
        for index, value in enumerate(("_openmcmProviderID as String", "_openmcmPageIndex as String",
                                       "_openmcmHostToken as String", "a_option as String", "a_text")):
            self.assertIn(f"params[{index}] = {value}", body)
        self.assertNotIn("optionCursor", self.sdk)
        self.assertNotRegex(self.sdk, r"(?im)^\s*(?:Parent\.)?(?:ForcePageReset|WriteOptionBuffers)\(")

    def test_text_updates_are_type_checked_and_capture_does_not_refresh_tokens(self):
        self.assertIn("_openmcmTypes[index] != OPTION_TYPE_TEXT", _body(self.sdk, "SetOptionText"))
        for name in ("GetPageToken", "IsPageTokenValid", "OpenMCM_IsPageContextValid", "OpenMCM_ResolveUpdate"):
            with self.subTest(name=name):
                self.assertNotRegex(_body(self.sdk, name), r"_openmcmPageToken\s*=(?!=)")
        public_guard = _body(self.sdk, "IsPageTokenValid")
        self.assertIn(".openMCMApiEnabled", public_guard)
        self.assertIn("Return OpenMCM_IsPageContextValid(a_token)", public_guard)
        validation = _body(self.sdk, "OpenMCM_IsPageContextValid")
        self.assertIn("a_token <= 0", validation)
        self.assertIn("a_token != _openmcmPageToken", validation)
        self.assertIn("_openmcmBuilding", validation)
        for getter in ("openMCMProviderID", "openMCMPageIndex", "openMCMPageToken"):
            self.assertIn(getter, validation)
        self.assertIn("hostMatches && a_token == _openmcmPageToken", validation)

    def test_help_update_captures_array_before_potentially_yielding_validation(self):
        body = _body(self.sdk, "SetOptionHelp")
        self.assertLess(body.index("String[] targetHelp = _openmcmHelp"),
                        body.index("OpenMCM_ResolveUpdate(a_key, a_token)"))
        self.assertIn("a_token != _openmcmPageToken", body)
        self.assertIn("targetHelp[index] = a_text", body)
        self.assertNotIn("_openmcmHelp[index] = a_text", body)


if __name__ == "__main__":
    unittest.main()
