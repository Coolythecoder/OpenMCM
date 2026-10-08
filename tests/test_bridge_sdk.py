"""Basic Bridge SDK source contracts and a binding model, not an in-game test.

These tests intentionally do not claim to execute Papyrus, native admission,
rendering or a real provider. The independently compiled PEX/package checks
must also run before packaging; Skyrim/MCM Bridge testing remains necessary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "src" / "compat" / "mcm-bridge"


def code(source: str) -> str:
    # A semicolon inside an error/help string is text, not a comment.
    return re.sub(r'"(?:\\.|[^"\\])*"|;[^\n]*',
                  lambda match: match.group() if match.group().startswith('"') else "", source)


def body(source: str, name: str, kind: str = "Function") -> str:
    match = re.search(
        rf"(?ims)^\s*(?:(?:Int|Bool|String|Float)\s+)?{kind}\s+{name}\s*"
        rf"\([^)]*\)[^\n]*\n(.*?)^\s*End{kind}\b", code(source)
    )
    if not match:
        raise AssertionError(f"missing {kind} {name}")
    return match.group(1).strip()


def signatures(source: str) -> dict[str, str]:
    result = {}
    for match in re.finditer(
        r"(?im)^\s*((?:(?:Int|Bool|String|Float)\s+)?(?:Function|Event)\s+"
        r"(\w+)\s*\([^)]*\)[^\n]*)", code(source)
    ):
        result[match.group(2).lower()] = re.sub(r"\s+", " ", match.group(1)).strip().lower()
    return result


@dataclass
class BindingModel:
    """Intended adapter invariants only; the parent host is a stub here."""

    page: int = -2
    building: bool = False
    cursor: int = 0
    fill: int = 1
    slots: dict[int, tuple[int, int, str]] = field(default_factory=dict)
    names: dict[str, int] = field(default_factory=dict)
    help: dict[int, str] = field(default_factory=dict)
    parent_calls: int = 0

    def clear(self) -> None:
        self.page = -2
        self.building = False
        self.cursor, self.fill = 0, 1
        self.slots.clear()
        self.names.clear()
        self.help.clear()

    def begin(self, page: int) -> None:
        self.clear()
        self.page = page
        self.building = True

    def position(self, position: int) -> None:
        if -1 <= position < 128:
            self.cursor = position

    def fill_mode(self, fill: int) -> None:
        if fill in (1, 2):
            self.fill = fill

    def add(self, option_type: int, state: str = "", fail_parent: bool = False) -> int:
        existing = self.slots.get(self.cursor)
        if self.building and existing and existing[2] and not state:
            return -1
        self.parent_calls += 1
        # Model the unchanged parent's valid page/cursor/result contract.
        if not self.building or fail_parent or not 0 <= self.cursor < 128:
            return -1
        slot = self.cursor
        option_id = slot + (self.page + 1) * 256
        self.names = {key: index for key, index in self.names.items() if index != slot}
        self.help.pop(slot, None)
        self.slots[slot] = option_id, option_type, state
        self.cursor = slot + self.fill
        if self.cursor >= 128:
            self.cursor = -1
        return option_id

    def bind(self, key: str, option_id: int, help_text: str = "") -> bool:
        key = key.lower()
        if not self.building or not key or key in self.names or option_id < 0:
            return False
        slot = option_id % 256
        existing = self.slots.get(slot)
        if (option_id // 256 != self.page + 1 or slot >= 128 or not existing
                or existing[0] != option_id or existing[1] == 0 or slot in self.names.values()):
            return False
        self.names[key] = slot
        self.help[slot] = help_text
        return True

    def bind_state(self, key: str, state: str) -> bool:
        for option_id, _, current_state in self.slots.values():
            if current_state and current_state.lower() == state.lower():
                return self.bind(key, option_id)
        return False

    def option_id(self, key: str) -> int:
        index = self.names.get(key.lower())
        return self.slots[index][0] if index is not None else -1


class BridgeSDKSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api = (ADAPTER / "OpenMCM.psc").read_text(encoding="utf-8")
        cls.sdk = (ADAPTER / "OpenMCM_ConfigBase.psc").read_text(encoding="utf-8")
        cls.original_api = (ROOT / "src/papyrus/OpenMCM.psc").read_text(encoding="utf-8")
        cls.original_sdk = (ROOT / "src/papyrus/OpenMCM_ConfigBase.psc").read_text(encoding="utf-8")

    def test_adapter_preserves_script_identity_and_parent(self):
        self.assertRegex(code(self.api), r"(?m)^Scriptname OpenMCM Hidden$")
        self.assertRegex(code(self.sdk), r"(?m)^Scriptname OpenMCM_ConfigBase extends SKI_ConfigBase$")

    def test_every_original_function_and_event_signature_remains(self):
        for original, adapter in ((self.original_api, self.api), (self.original_sdk, self.sdk)):
            adapter_signatures = signatures(adapter)
            for name, signature in signatures(original).items():
                with self.subTest(name=name):
                    self.assertEqual(adapter_signatures.get(name), signature)

    def test_original_saved_fields_keep_types_and_names(self):
        def by_name(source):
            preamble = code(source).split("Event OnGameReload", 1)[0]
            return {name: kind for kind, name in re.findall(
                r"(?im)^\s*(String\[\]|Int\[\]|Int|Bool)\s+(_openmcm\w+)", preamble)}
        adapter_fields = by_name(self.sdk)
        for name, kind in by_name(self.original_sdk).items():
            self.assertEqual(adapter_fields.get(name), kind, name)
        self.assertTrue(all(name.startswith("_openmcm") for name in adapter_fields))

    def test_only_named_capability_is_advertised(self):
        self.assertEqual(body(self.api, "HasCapability"), 'Return a_capability == "named_options"')
        self.assertEqual(body(self.api, "GetAPIVersion"), "Return 1")
        self.assertEqual(body(self.api, "IsAPIEnabled"), "Return False")
        self.assertEqual(body(self.api, "GetHostAPIVersion"), "Return 0")

    def test_optional_operations_are_fail_closed_without_side_effects(self):
        false_methods = ("IsPageTokenValid", "OpenMCM_IsPageContextValid", "SetOptionLabel",
                         "SetOptionText", "SetOptionHelp", "SetLiveInfoText", "SetCurrentPage",
                         "SetOptionsEnabled")
        for name in false_methods:
            with self.subTest(name=name):
                self.assertEqual(body(self.sdk, name), "Return False")
        for name in ("GetPageToken", "OpenMCM_CapturePageToken"):
            self.assertEqual(body(self.sdk, name), "Return 0")
        self.assertEqual(body(self.sdk, "OpenMCM_ResolveUpdate"), "Return -1")
        self.assertEqual(body(self.sdk, "OpenMCM_DefaultHelp"), 'Return ""')
        for name in ("OpenMCM_SendText", "OpenMCM_PublishHelp"):
            self.assertEqual(body(self.sdk, name), "")

    def test_no_journal_manager_or_native_replacement_calls(self):
        combined = code(self.api + self.sdk)
        self.assertNotRegex(combined, r"\b(?:UI|Game|MCMBridgeNative|SKI_ConfigManager)\s*[.(]")
        self.assertNotRegex(combined, r"\b(?:MENU_ROOT|JOURNAL_MENU|IsOpenMCMAPIEnabled|OpenMCM_GetConfigID|OpenMCM_ClearOptionState)\b")
        self.assertNotRegex(combined, r"(?i)\bNative\b")

    def test_lifecycle_invalidates_bindings_before_parent(self):
        for name, kind, call in (
                ("OnGameReload", "Event", "Parent.OnGameReload()"),
                ("OnConfigManagerReset", "Event", "Parent.OnConfigManagerReset("),
                ("CloseConfig", "Function", "Parent.CloseConfig()"),
                ("SetPage", "Function", "Parent.SetPage(")):
            content = body(self.sdk, name, kind)
            self.assertLess(content.index("OpenMCM_ClearPage()"), content.index(call))

    def test_parent_owns_page_admission_and_callback_dispatch(self):
        content = body(self.sdk, "SetPage")
        self.assertLess(content.index("_openmcmBuilding = True"), content.index("Parent.SetPage("))
        self.assertGreater(content.index("_openmcmBuilding = False"), content.index("Parent.SetPage("))
        self.assertNotIn("OnPageReset(", content)
        declared = signatures(self.sdk)
        for name in ("HighlightOption", "SetInfoText", "SelectOption", "BridgeEnterCall", "BridgeLeaveCall",
                     "BindNativeHost", "OnConfigManagerReady", "OpenConfig", "GetVersion"):
            self.assertNotIn(name.lower(), declared)

    def test_clear_buffers_resets_metadata_and_delegates_to_bridge(self):
        content = body(self.sdk, "ClearOptionBuffers")
        self.assertIn("Parent.ClearOptionBuffers()", content)
        for name, kind in (("Keys", "String"), ("Help", "String"), ("IDs", "Int"),
                           ("Types", "Int"), ("BridgeStates", "String")):
            self.assertIn(f"_openmcm{name} = New {kind}[128]", content)
        self.assertIn("_openmcmBridgeCursor = 0", content)
        self.assertIn("_openmcmBridgeFillMode = 1", content)

    def test_cleared_scope_cannot_reuse_saved_tokens_or_old_names(self):
        content = body(self.sdk, "OpenMCM_ClearPage")
        for name in ("PageToken", "HostToken"):
            self.assertIn(f"_openmcm{name} = 0", content)
        self.assertIn("_openmcmBuilding = False", content)
        self.assertIn("_openmcmPageIndex = -2", content)
        for name, kind in (("Keys", "String"), ("Help", "String"), ("IDs", "Int"),
                           ("Types", "Int"), ("BridgeStates", "String")):
            self.assertIn(f"_openmcm{name} = New {kind}[1]", content)

    def test_shared_bridge_addition_hook_tracks_normal_and_state_rows(self):
        content = body(self.sdk, "BridgeAddOption")
        self.assertIn("Parent.BridgeAddOption(a_type, a_label, a_text, a_number, a_flags, a_state)", content)
        for line in ('_openmcmKeys[index] = ""', '_openmcmHelp[index] = ""',
                     "_openmcmIDs[index] = optionID", "_openmcmTypes[index] = a_type",
                     "_openmcmBridgeStates[index] = a_state"):
            self.assertIn(line, content)
        self.assertIn("Return Parent.AddOption(", body(self.sdk, "AddOption"))
        self.assertNotIn("addoptionst", signatures(self.sdk))

    def test_st_to_ordinary_replacement_rejects_before_host_mutation(self):
        content = body(self.sdk, "BridgeAddOption")
        rejection = content.index('If a_state == "" && _openmcmBridgeStates[_openmcmBridgeCursor] != ""')
        failure = content.index("Return -1", rejection)
        self.assertLess(failure, content.index("Parent.BridgeAddOption("))

    def test_invalid_host_ids_are_rejected_before_array_indexing(self):
        content = body(self.sdk, "BridgeAddOption")
        self.assertIn("optionID >= 0 && _openmcmBuilding", content)
        self.assertIn("index >= 128", content)
        self.assertIn("(optionID / 0x100) != (_openmcmPageIndex + 1)", content)
        self.assertLess(content.index("index >= 128"), content.index('_openmcmKeys[index] = ""'))

    def test_cursor_mirrors_match_valid_parent_ranges(self):
        position = body(self.sdk, "SetCursorPosition")
        self.assertIn("Parent.SetCursorPosition(a_position)", position)
        self.assertIn("a_position >= -1 && a_position < 128", position)
        fill = body(self.sdk, "SetCursorFillMode")
        self.assertIn("Parent.SetCursorFillMode(a_fillMode)", fill)
        self.assertIn("a_fillMode == LEFT_TO_RIGHT || a_fillMode == TOP_TO_BOTTOM", fill)
        advance = body(self.sdk, "BridgeAddOption")
        self.assertIn("_openmcmBridgeCursor = index + _openmcmBridgeFillMode", advance)
        self.assertIn("_openmcmBridgeCursor >= 128", advance)
        self.assertIn("_openmcmBridgeCursor = -1", advance)

    def test_binding_validates_scope_keys_namespace_type_and_unique_slot(self):
        can = body(self.sdk, "OpenMCM_CanBind")
        for fragment in ("!_openmcmBuilding", "_openmcmKeys.Length != 128", 'a_key == ""',
                         "_openmcmKeys.Find(a_key) >= 0"):
            self.assertIn(fragment, can)
        resolve = body(self.sdk, "OpenMCM_ResolveID")
        for fragment in ("a_option < 0", "(a_option / 0x100) != (_openmcmPageIndex + 1)",
                         "index >= 128", "_openmcmIDs[index] != a_option",
                         "_openmcmTypes[index] == OPTION_TYPE_EMPTY"):
            self.assertIn(fragment, resolve)
        self.assertIn('_openmcmKeys[index] != ""', body(self.sdk, "BindOption"))
        state = body(self.sdk, "BindStateOption")
        self.assertIn("GetStateOptionIndex(a_stateName)", state)
        self.assertIn("BindOption(a_key, index + ((_openmcmPageIndex + 1) * 0x100), a_help)", state)

    def test_all_eight_named_controls_keep_original_types_and_payloads(self):
        for suffix in ("Header", "Text", "Toggle", "Slider", "Menu", "Color", "KeyMap", "Input"):
            with self.subTest(kind=suffix):
                self.assertEqual(body(self.sdk, "AddNamed" + suffix),
                                 body(self.original_sdk, "AddNamed" + suffix))


class BridgeSDKBindingModelTests(unittest.TestCase):
    """No model test is evidence of a working Skyrim/Papyrus runtime."""

    def setUp(self):
        self.model = BindingModel()
        self.model.begin(0)

    def test_initial_unnamed_page_uses_zero_namespace(self):
        self.model.begin(-1)
        option = self.model.add(2)
        self.assertEqual(option, 0)
        self.assertTrue(self.model.bind("initial", option))
        self.assertEqual(self.model.option_id("INITIAL"), 0)

    def test_first_and_last_valid_slots_keep_full_page_ids(self):
        first = self.model.add(2)
        self.model.position(127)
        last = self.model.add(2)
        self.assertEqual((first, last, self.model.cursor), (256, 383, -1))
        self.assertTrue(self.model.bind("first", first))
        self.assertTrue(self.model.bind("last", last))
        self.assertEqual(self.model.option_id("LAST"), 383)
        self.assertEqual(self.model.add(2), -1)

    def test_stale_namespace_or_invalid_slot_cannot_bind(self):
        self.model.add(2)
        for option in (-1, 0, 128, 384, 511, 512):
            with self.subTest(option=option):
                self.assertFalse(self.model.bind("invalid", option))

    def test_empty_type_unallocated_slot_and_empty_key_cannot_bind(self):
        empty = self.model.add(0)
        header = self.model.add(1)
        self.assertFalse(self.model.bind("empty", empty))
        self.assertFalse(self.model.bind("unallocated", 300))
        self.assertFalse(self.model.bind("", header))
        self.assertTrue(self.model.bind("header", header))

    def test_duplicate_keys_and_second_name_for_slot_do_not_replace(self):
        first, second = self.model.add(2), self.model.add(3)
        self.assertTrue(self.model.bind("First", first, "Original"))
        before = dict(self.model.names), dict(self.model.help)
        self.assertFalse(self.model.bind("FIRST", second))
        self.assertFalse(self.model.bind("alias", first))
        self.assertEqual((self.model.names, self.model.help), before)

    def test_binding_only_allowed_during_build(self):
        option = self.model.add(2)
        self.model.building = False
        self.assertFalse(self.model.bind("late", option))

    def test_state_option_can_bind_without_ordinary_add_path(self):
        option = self.model.add(2, state="ResetChecklist")
        self.assertTrue(self.model.bind_state("clear", "resetchecklist"))
        self.assertEqual(self.model.option_id("clear"), option)
        self.assertFalse(self.model.bind_state("missing", "NoSuchState"))

    def test_failed_parent_add_does_not_remove_existing_binding_or_advance_cursor(self):
        first = self.model.add(2)
        self.model.bind("first", first, "Keep")
        self.model.position(0)
        self.assertEqual(self.model.add(3, fail_parent=True), -1)
        self.assertEqual(self.model.option_id("first"), first)
        self.assertEqual(self.model.help[0], "Keep")
        self.assertEqual(self.model.cursor, 0)

    def test_unnamed_overwrite_clears_previous_key_and_help(self):
        first = self.model.add(2)
        self.model.bind("first", first, "Old help")
        self.model.position(0)
        self.assertEqual(self.model.add(3), first)
        self.assertEqual(self.model.option_id("first"), -1)
        self.assertNotIn(0, self.model.help)
        self.assertTrue(self.model.bind("replacement", first))

    def test_ordinary_to_state_replacement_clears_old_name(self):
        first = self.model.add(2)
        self.model.bind("first", first)
        self.model.position(0)
        self.assertEqual(self.model.add(2, state="ResetChecklist"), first)
        self.assertEqual(self.model.option_id("first"), -1)
        self.assertTrue(self.model.bind_state("clear", "ResetChecklist"))

    def test_state_to_ordinary_replacement_is_rejected_before_parent_call(self):
        first = self.model.add(2, state="ResetChecklist")
        self.model.bind_state("clear", "ResetChecklist")
        self.model.position(0)
        before = self.model.parent_calls
        self.assertEqual(self.model.add(2), -1)
        self.assertEqual(self.model.parent_calls, before)
        self.assertEqual(self.model.cursor, 0)
        self.assertEqual(self.model.option_id("clear"), first)
        self.assertEqual(self.model.slots[0][2], "ResetChecklist")

    def test_rebuilding_allows_old_state_slot_to_become_ordinary(self):
        self.model.add(2, state="ResetChecklist")
        self.model.begin(0)
        self.assertEqual(self.model.add(2), 256)
        self.assertTrue(self.model.bind("ordinary", 256))

    def test_column_fill_rewind_and_invalid_positions(self):
        self.model.fill_mode(2)
        self.assertEqual([self.model.add(2) for _ in range(3)], [256, 258, 260])
        self.model.position(1)
        self.assertEqual(self.model.add(2), 257)
        for position in (-2, 128, 999):
            self.model.position(position)
            self.assertEqual(self.model.cursor, 3)
        for fill in (-1, 0, 3):
            self.model.fill_mode(fill)
            self.assertEqual(self.model.fill, 2)
        self.model.position(-1)
        self.assertEqual(self.model.add(2), -1)

    def test_close_reload_reset_or_page_clear_removes_metadata(self):
        self.model.add(2, state="ResetChecklist")
        self.model.bind_state("clear", "ResetChecklist")
        self.model.clear()
        self.assertEqual(self.model.option_id("clear"), -1)
        self.assertEqual((self.model.slots, self.model.names, self.model.help), ({}, {}, {}))
        self.assertFalse(self.model.building)
        self.assertEqual(self.model.page, -2)


if __name__ == "__main__":
    unittest.main()
