"""Runtime opt-in source contracts and behavior-model specifications.

The models below describe persistence and capability boundaries; they do not
execute Papyrus, emulate the game VM, or prove save migration. Actual compiled
scripts, host/AVM1 tests and in-game checks remain separate verification layers.
"""
from __future__ import annotations

import re
import unittest
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _code(source: str) -> str:
    """Remove line comments without altering semicolons inside strings."""
    return re.sub(r'("[^"\r\n]*")|;[^\r\n]*', lambda match: match.group(1) or "", source)


def _function(source: str, name: str) -> str:
    match = re.search(
        rf"(?ims)^\s*(?:(?:int|bool|string|float)\s+)?function\s+{re.escape(name)}"
        rf"\s*\([^)]*\)(?:\s+global)?(.*?)^\s*endfunction\b", _code(source))
    if match is None:
        raise AssertionError(f"missing Papyrus function {name}")
    return match.group(1)


def _event(source: str, name: str) -> str:
    match = re.search(
        rf"(?ims)^\s*event\s+{re.escape(name)}\s*\([^)]*\)(.*?)^\s*endevent\b",
        _code(source))
    if match is None:
        raise AssertionError(f"missing Papyrus event {name}")
    return match.group(1)


def _state(source: str, name: str) -> str:
    match = re.search(
        rf"(?ims)^\s*state\s+{re.escape(name)}\b(.*?)^\s*endstate\b", _code(source))
    if match is None:
        raise AssertionError(f"missing Papyrus state {name}")
    return match.group(1)


class RuntimeToggleSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manager = (ROOT / "src/papyrus/SKI_ConfigManager.psc").read_text(encoding="utf-8")
        cls.api = (ROOT / "src/papyrus/OpenMCM.psc").read_text(encoding="utf-8")
        cls.menu = (ROOT / "src/papyrus/OpenMCM_ConfigMenu.psc").read_text(encoding="utf-8")
        cls.sdk = (ROOT / "src/papyrus/OpenMCM_ConfigBase.psc").read_text(encoding="utf-8")

    def test_manager_appends_saved_preference_with_safe_default(self) -> None:
        declarations = _code(self.manager).split("Int Function GetVersion", 1)[0]
        self.assertRegex(declarations, r"(?m)^Bool _openmcmAPIEnabled = False\s*$")
        self.assertGreater(declarations.index("Bool _openmcmAPIEnabled"),
                           declarations.index("Bool _registryBusy"))
        self.assertEqual(_function(self.manager, "IsOpenMCMAPIEnabled").strip(),
                         "Return _openmcmAPIEnabled")

    def test_only_default_and_setter_assign_saved_preference(self) -> None:
        assignments = re.findall(r"(?im)^\s*(?:Bool\s+)?_openmcmAPIEnabled\s*=\s*([^\r\n]+)",
                                 _code(self.manager))
        self.assertEqual(assignments, ["False", "a_enabled"])

    def test_reload_and_registry_repair_do_not_reset_preference(self) -> None:
        for body in (_event(self.manager, "OnGameReload"),
                     _function(self.manager, "ForceReset"),
                     _function(self.manager, "OpenMCM_TryForceReset"),
                     _function(self.manager, "InitializeStorage")):
            self.assertNotRegex(body, r"(?i)_openmcmAPIEnabled\s*=")

    def test_setter_stores_before_publishing(self) -> None:
        body = _function(self.manager, "SetOpenMCMAPIEnabled")
        self.assertLess(body.index("_openmcmAPIEnabled = a_enabled"),
                        body.index("PublishOpenMCMAPIState()"))

    def test_closed_journal_never_gets_enable_invocation(self) -> None:
        body = _function(self.manager, "PublishOpenMCMAPIState")
        self.assertRegex(body, r"(?is)If !UI\.IsMenuOpen\(JOURNAL_MENU\)\s+Return\s+EndIf")
        self.assertIn('UI.InvokeBool(JOURNAL_MENU, MENU_ROOT + ".setOpenMCMAPIEnabled", _openmcmAPIEnabled)', body)
        self.assertLess(body.index("UI.IsMenuOpen"), body.index("UI.InvokeBool"))

    def test_movie_resync_publishes_preference_before_provider_names(self) -> None:
        body = _function(self.manager, "PublishModList")
        self.assertIn("PublishOpenMCMAPIState()", body)
        self.assertLess(body.index("PublishOpenMCMAPIState()"), body.index('".setModNames"'))

    def test_public_preference_getter_resolves_shared_manager_and_fails_closed(self) -> None:
        body = _function(self.api, "IsAPIEnabled")
        self.assertIn('Game.GetFormFromFile(0x000802, "SkyUI_SE.esp") as SKI_ConfigManager', body)
        self.assertIn("Return manager != None && manager.IsOpenMCMAPIEnabled()", body)
        self.assertNotIn("UI.", body)  # Readable outside the Journal too.
        self.assertRegex(_code(self.api), r"(?im)^Bool Function IsAPIEnabled\(\) Global\s*$")

    def test_sdk_and_skyui_versions_remain_separate(self) -> None:
        self.assertIn("Return 1", _function(self.api, "GetAPIVersion"))
        self.assertIn("Return 4", _function(self.manager, "GetVersion"))
        self.assertNotIn("IsAPIEnabled", _function(self.api, "HasCapability"))

    def test_enable_option_and_version_are_in_runtime_section(self) -> None:
        body = _event(self.menu, "OnPageReset")
        runtime = body.split('AddHeaderOption("Runtime")', 1)[1].split('AddHeaderOption("Compatibility")', 1)[0]
        self.assertIn('AddTextOption("OpenMCM API", "Version " + OpenMCM.GetAPIVersion())', runtime)
        self.assertIn('AddToggleOptionST("ExtendedAPI", "Enable OpenMCM API", OpenMCM.IsAPIEnabled())', runtime)
        self.assertIn('AddTextOption("SkyUI MCM API", "Version 4")', runtime)

    def test_menu_persists_choice_then_rebuilds_page(self) -> None:
        body = _function(self.menu, "SetExtendedAPIEnabled")
        self.assertIn('Game.GetFormFromFile(0x000802, "SkyUI_SE.esp") as SKI_ConfigManager', body)
        self.assertRegex(body, r"(?s)If manager != None\s+manager\.SetOpenMCMAPIEnabled\(a_enabled\)\s+EndIf")
        self.assertLess(body.index("manager.SetOpenMCMAPIEnabled(a_enabled)"), body.index("ForcePageReset()"))

    def test_toggle_and_default_use_same_persistence_path(self) -> None:
        state = _state(self.menu, "ExtendedAPI")
        self.assertIn("SetExtendedAPIEnabled(!OpenMCM.IsAPIEnabled())", _event(state, "OnSelectST"))
        self.assertIn("SetExtendedAPIEnabled(False)", _event(state, "OnDefaultST"))

    def test_help_explains_scope_without_promising_crash_fix(self) -> None:
        help_body = _event(_state(self.menu, "ExtendedAPI"), "OnHighlightST").lower()
        for phrase in ("automatic help", "live text", "mods written for openmcm", "off by default",
                       "savegame", "skyui api 4", "mcm helper", "normal controls stay available",
                       "no native dll required", "does not upgrade existing mcms or fix exit crashes"):
            self.assertIn(phrase, help_body)

    def test_public_token_requires_enabled_host_before_context_validation(self) -> None:
        body = _function(self.sdk, "IsPageTokenValid")
        self.assertRegex(body, r'(?s)If !UI\.GetBool\(JOURNAL_MENU, MENU_ROOT \+ "\.openMCMApiEnabled"\)\s+Return False\s+EndIf')
        self.assertLess(body.index("UI.GetBool"), body.index("OpenMCM_IsPageContextValid(a_token)"))
        getter = _function(self.sdk, "GetPageToken")
        self.assertIn("If IsPageTokenValid(_openmcmPageToken)", getter)
        self.assertIn("Return 0", getter)

    def test_internal_context_keeps_full_staleness_checks_without_opt_in(self) -> None:
        body = _function(self.sdk, "OpenMCM_IsPageContextValid")
        for fragment in ("a_token <= 0", "a_token != _openmcmPageToken", "_openmcmBuilding",
                         '".openMCMProviderID"', '".openMCMPageIndex"', '".openMCMPageToken"',
                         "_openmcmHostToken"):
            self.assertIn(fragment, body)
        self.assertNotIn("openMCMApiEnabled", body)

    def test_explicit_legacy_help_uses_internal_context_and_separate_endpoint(self) -> None:
        capture = _function(self.sdk, "OpenMCM_CapturePageToken")
        publish = _function(self.sdk, "OpenMCM_PublishHelp")
        self.assertIn("OpenMCM_IsPageContextValid(_openmcmPageToken)", capture)
        self.assertIn("OpenMCM_IsPageContextValid(a_token)", publish)
        self.assertIn('OpenMCM_SendText("openMCMSetHighlightText"', publish)
        self.assertNotIn("IsPageTokenValid", capture + publish)
        self.assertNotIn("openMCMApiEnabled", capture + publish)

    def test_only_automatic_help_is_opt_in(self) -> None:
        body = _function(self.sdk, "OpenMCM_DefaultHelp")
        self.assertRegex(body, r'(?s)If !UI\.GetBool\(JOURNAL_MENU, MENU_ROOT \+ "\.openMCMApiEnabled"\)\s+Return ""\s+EndIf')
        self.assertLess(body.index("UI.GetBool"), body.index("Return _openmcmHelp[a_index]"))

    def test_named_controls_and_bindings_remain_usable_for_legacy_fallback(self) -> None:
        for name in ("BindOption", "BindStateOption", "GetOptionID", "OpenMCM_CanBind", "OpenMCM_AddNamed"):
            body = _function(self.sdk, name)
            self.assertNotIn("IsPageTokenValid", body)
            self.assertNotIn("openMCMApiEnabled", body)
        self.assertIn("AddOption(a_type, a_text, a_value, a_number, a_flags)",
                      _function(self.sdk, "OpenMCM_AddNamed"))

    def test_runtime_toggle_has_no_native_plugin_or_polling_dependency(self) -> None:
        bodies = (_function(self.api, "IsAPIEnabled") +
                  _function(self.manager, "SetOpenMCMAPIEnabled") +
                  _function(self.manager, "PublishOpenMCMAPIState") +
                  _function(self.menu, "SetExtendedAPIEnabled") + _state(self.menu, "ExtendedAPI"))
        # Restrict the assertion to implementation tokens, not explanatory text.
        implementation = re.sub(r'"[^"\r\n]*"', '""', bodies)
        self.assertNotRegex(implementation, r"(?i)\b(?:native|OpenMCMRuntime|RegisterForUpdate|RegisterForSingleUpdate|RegisterForKey|RegisterForControl|Wait|WaitMenuMode)\b")


@dataclass
class _HostModel:
    """Specification model only: no Scaleform/AVM1 code is executed here."""
    enabled: bool = False
    generation: int = 0
    ready: bool = False
    writes: list[tuple] = field(default_factory=list)

    def set_enabled(self, enabled: bool) -> None:
        if self.enabled != enabled:
            self.enabled = enabled
            self.generation += 1
            self.ready = False
        self.writes.append(("enabled", enabled))

    def flush_page(self) -> int:
        self.generation += 1
        self.ready = True
        return self.generation

    def context_valid(self, token: int) -> bool:
        return self.ready and token > 0 and token == self.generation

    def public_token(self) -> int:
        return self.generation if self.enabled and self.ready else 0

    def live_text(self, token: int, text: str) -> bool:
        if not self.enabled or not self.context_valid(token):
            return False
        self.writes.append(("live", text))
        return True

    def highlight(self, token: int, default_help: str, explicit_help: str | None = None) -> bool:
        if not self.context_valid(token):
            return False
        text = default_help if self.enabled else ""
        if explicit_help is not None:
            text = explicit_help
        self.writes.append(("help", text))
        return True


@dataclass
class _ManagerModel:
    """Specification model only: saved bool survives reload/registry rebuild."""
    enabled: bool = False
    host: _HostModel | None = None

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.publish_preference()

    def publish_preference(self) -> None:
        if self.host is not None:
            self.host.set_enabled(self.enabled)

    def publish_mod_list(self) -> None:
        if self.host is not None:
            self.publish_preference()
            self.host.writes.append(("mods", "registered providers"))

    def reload(self) -> None:
        self.host = None

    def rebuild_registry(self) -> None:
        self.publish_mod_list()


class RuntimeToggleBehaviorModelTests(unittest.TestCase):
    """Intended behavior invariants, deliberately not claimed as VM tests."""

    def test_new_and_old_save_default_is_disabled(self) -> None:
        self.assertFalse(_ManagerModel().enabled)
        host = _HostModel()
        host.flush_page()
        self.assertEqual(host.public_token(), 0)

    def test_closed_menu_preference_is_persisted_and_deferred(self) -> None:
        manager = _ManagerModel()
        manager.set_enabled(True)
        self.assertTrue(manager.enabled)
        self.assertIsNone(manager.host)
        manager.host = _HostModel()
        manager.publish_mod_list()
        self.assertEqual(manager.host.writes[:2], [("enabled", True), ("mods", "registered providers")])

    def test_menu_recreation_and_reload_restore_saved_preference(self) -> None:
        manager = _ManagerModel(True, _HostModel())
        manager.publish_mod_list()
        manager.reload()
        self.assertTrue(manager.enabled)
        manager.host = _HostModel()
        self.assertFalse(manager.host.enabled)
        manager.publish_mod_list()
        self.assertTrue(manager.host.enabled)

    def test_registry_rebuild_does_not_change_user_preference(self) -> None:
        for choice in (False, True):
            manager = _ManagerModel(choice, _HostModel())
            manager.rebuild_registry()
            self.assertEqual(manager.enabled, choice)
            self.assertEqual(manager.host.enabled, choice)

    def test_enabling_requires_a_fresh_page_before_live_work(self) -> None:
        host = _HostModel()
        old = host.flush_page()
        host.set_enabled(True)
        self.assertEqual(host.public_token(), 0)
        self.assertFalse(host.live_text(old, "stale"))
        fresh = host.flush_page()
        self.assertEqual(host.public_token(), fresh)
        self.assertTrue(host.live_text(fresh, "new work"))

    def test_disabling_rejects_pending_live_work(self) -> None:
        host = _HostModel(True)
        old = host.flush_page()
        host.set_enabled(False)
        self.assertFalse(host.live_text(old, "pending before disable"))
        host.flush_page()
        self.assertEqual(host.public_token(), 0)

    def test_reenable_never_resurrects_old_token(self) -> None:
        host = _HostModel(True)
        old = host.flush_page()
        host.set_enabled(False)
        host.set_enabled(True)
        new = host.flush_page()
        self.assertNotEqual(old, new)
        self.assertFalse(host.live_text(old, "old action"))
        self.assertTrue(host.live_text(new, "fresh action"))

    def test_repeated_preference_resync_keeps_current_page_valid(self) -> None:
        host = _HostModel(True)
        current = host.flush_page()
        manager = _ManagerModel(True, host)
        manager.publish_mod_list()
        manager.publish_mod_list()
        self.assertTrue(host.context_valid(current))
        self.assertEqual(host.public_token(), current)

    def test_off_keeps_explicit_legacy_help_but_suppresses_automatic_help(self) -> None:
        host = _HostModel()
        current = host.flush_page()
        self.assertTrue(host.highlight(current, "automatic"))
        self.assertEqual(host.writes[-1], ("help", ""))
        self.assertTrue(host.highlight(current, "automatic", "author callback"))
        self.assertEqual(host.writes[-1], ("help", "author callback"))

    def test_on_allows_automatic_help_and_explicit_empty_override(self) -> None:
        host = _HostModel(True)
        current = host.flush_page()
        self.assertTrue(host.highlight(current, "automatic"))
        self.assertEqual(host.writes[-1], ("help", "automatic"))
        self.assertTrue(host.highlight(current, "automatic", ""))
        self.assertEqual(host.writes[-1], ("help", ""))

    def test_legacy_help_still_rejects_stale_scope_while_off(self) -> None:
        host = _HostModel()
        stale = host.flush_page()
        host.flush_page()
        self.assertFalse(host.highlight(stale, "", "wrong page callback"))
        self.assertEqual(host.writes, [])

    def test_default_action_disables_and_persists_across_reload(self) -> None:
        manager = _ManagerModel(True, _HostModel(True))
        manager.host.flush_page()
        manager.set_enabled(False)
        self.assertFalse(manager.host.enabled)
        manager.reload()
        manager.host = _HostModel()
        manager.publish_mod_list()
        self.assertFalse(manager.enabled)
        self.assertFalse(manager.host.enabled)


if __name__ == "__main__":
    unittest.main()
