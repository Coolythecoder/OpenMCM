from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANAGER_PATH = REPOSITORY_ROOT / "src" / "papyrus" / "SKI_ConfigManager.psc"
BASE_PATH = REPOSITORY_ROOT / "src" / "papyrus" / "SKI_ConfigBase.psc"


def _papyrus_body(source: str, declaration: str, terminator: str) -> str:
    match = re.search(
        rf"(?is){re.escape(declaration)}\s*(.*?)\b{re.escape(terminator)}\b",
        source,
    )
    if not match:
        raise AssertionError(f"missing {declaration}")
    return match.group(1)


def _function(source: str, declaration: str) -> str:
    return _papyrus_body(source, declaration, "EndFunction")


def _event(source: str, declaration: str) -> str:
    return _papyrus_body(source, declaration, "EndEvent")


class RegistryRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manager = MANAGER_PATH.read_text(encoding="utf-8")
        cls.base = BASE_PATH.read_text(encoding="utf-8")

    def test_upgrade_flags_are_appended_after_original_saved_fields(self) -> None:
        update_counter = self.manager.index("Int _updateCounter = 0")
        rebuilt = self.manager.index("Bool _storageRebuilt = False")
        menu_open = self.manager.index("Bool _menuOpen = False")
        registry_busy = self.manager.index("Bool _registryBusy = False")
        get_version = self.manager.index("Int Function GetVersion()")
        self.assertLess(update_counter, rebuilt)
        self.assertLess(rebuilt, menu_open)
        self.assertLess(menu_open, registry_busy)
        self.assertLess(registry_busy, get_version)

    def test_on_init_matches_skyui_storage_allocation_order(self) -> None:
        on_init = _event(self.manager, "Event OnInit()")
        self.assertEqual(on_init.count("OnGameReload()"), 1)
        self.assertNotIn("InitializeStorage()", on_init)
        self.assertLess(
            on_init.index("_modConfigs = New SKI_ConfigBase[128]"),
            on_init.index("_modNames = New String[128]"),
        )
        self.assertLess(
            on_init.index("_modNames = New String[128]"),
            on_init.index("OnGameReload()"),
        )

    def test_missing_object_registry_resets_all_parallel_state(self) -> None:
        initialize = _function(self.manager, "Function InitializeStorage()")
        for statement in (
            "_modConfigs = New SKI_ConfigBase[128]",
            "_modNames = New String[128]",
            "_configCount = 0",
            "_curConfigID = 0",
            "_addCounter = 0",
            "_activeConfig = None",
            "_storageRebuilt = True",
        ):
            self.assertIn(statement, initialize)

        # If object references survived, do not discard them merely because the
        # parallel display-name cache was absent.
        self.assertEqual(initialize.count("New SKI_ConfigBase"), 1)
        self.assertIn("If _modNames == None", initialize)
        self.assertIn("_modNames[i] = _modConfigs[i].ModName", initialize)

    def test_registration_never_reports_success_without_valid_storage(self) -> None:
        register = _function(
            self.manager,
            "Int Function RegisterMod(SKI_ConfigBase a_menu, String a_modName)",
        )
        storage_guard = register.index("If !HasValidStorage()")
        first_registry_read = register.index("_modConfigs.Find(a_menu)")
        self.assertLess(storage_guard, first_registry_read)
        guard_body = register[storage_guard:first_registry_read]
        self.assertIn("_registryBusy = False", guard_body)
        self.assertIn('GotoState("")', guard_body)
        self.assertIn("Return -1", guard_body)

        write = register.index("_modConfigs[newID] = a_menu")
        persisted = register.index("If _modConfigs[newID] != a_menu")
        success = register.index("Return newID")
        self.assertLess(write, persisted)
        self.assertLess(persisted, success)

    def test_cleanup_derives_names_from_authoritative_menu_objects(self) -> None:
        cleanup = _function(self.manager, "Function CleanUp()")
        valid_entry = cleanup.rsplit("Else", maxsplit=1)[1]
        self.assertIn("_modNames[i] = _modConfigs[i].ModName", valid_entry)
        self.assertIn("_configCount += 1", valid_entry)

    def test_reload_resets_clients_before_announcing_repaired_registry(self) -> None:
        reload_body = _event(self.manager, "Event OnGameReload()")
        self.assertIn("If _storageRebuilt", reload_body)
        self.assertLess(
            reload_body.index('SendModEvent("SKICP_configManagerReset")'),
            reload_body.index('SendModEvent("SKICP_configManagerReady")'),
        )

    def test_update_recovers_a_busy_state_saved_outside_the_journal(self) -> None:
        update = _event(self.manager, "Event OnUpdate()")
        busy_guard = update.index("If _registryBusy")
        recovery = update.index("If !_menuOpen")
        self.assertLess(busy_guard, recovery)
        self.assertIn("RegisterForSingleUpdate(1.0)", update[busy_guard:recovery])
        self.assertIn("Return", update[busy_guard:recovery])
        self.assertIn("If !_menuOpen", update)
        self.assertIn('GotoState("")', update)
        self.assertIn("InitializeStorage()", update)
        self.assertIn('SendModEvent("SKICP_configManagerReset")', update)
        self.assertLess(
            update.index('SendModEvent("SKICP_configManagerReset")'),
            update.index('SendModEvent("SKICP_configManagerReady")'),
        )

    def test_menu_open_tracking_distinguishes_real_and_stale_busy_states(self) -> None:
        opened = _event(self.manager, "Event OnMenuOpen(String a_menuName)")
        closed = _event(self.manager, "Event OnMenuClose(String a_menuName)")
        self.assertLess(opened.index("_menuOpen = True"), opened.index('GotoState("BUSY")'))
        self.assertLess(closed.index("_menuOpen = False"), closed.index('GotoState("")'))
        self.assertNotIn('SendModEvent("SKICP_configManagerReady")', closed)
        self.assertIn("_activeConfig.CloseConfig()", closed)
        self.assertIn("_activeConfig = None", closed)

    def test_registry_mutations_protect_the_busy_state_recovery(self) -> None:
        for declaration in (
            "Int Function RegisterMod(SKI_ConfigBase a_menu, String a_modName)",
            "Int Function UnregisterMod(SKI_ConfigBase a_menu)",
            "Bool Function OpenMCM_TryForceReset()",
            "Function CleanUp()",
        ):
            body = _function(self.manager, declaration)
            self.assertIn("If _registryBusy", body)
            self.assertIn("_registryBusy = True", body)
            self.assertIn("_registryBusy = False", body)

    def test_force_reset_consumes_any_storage_rebuild_marker(self) -> None:
        force_reset = _function(self.manager, "Bool Function OpenMCM_TryForceReset()")
        self.assertIn("_storageRebuilt = False", force_reset)
        self.assertLess(
            force_reset.index("_storageRebuilt = False"),
            force_reset.index('SendModEvent("SKICP_configManagerReady")'),
        )

    def test_legacy_force_reset_keeps_void_abi_and_delegates_to_acknowledged_path(self) -> None:
        force_reset = _function(self.manager, "Function ForceReset()")
        implementation = re.sub(r";[^\r\n]*", "", force_reset).strip()
        self.assertEqual(implementation, "OpenMCM_TryForceReset()")
        busy_state = self.manager.split("State BUSY", 1)[1]
        self.assertEqual(_function(busy_state, "Function ForceReset()").strip(), "")

    def test_reset_acknowledgement_rejects_busy_state_explicitly(self) -> None:
        busy_state = self.manager.split("State BUSY", 1)[1]
        self.assertEqual(
            _function(busy_state, "Bool Function OpenMCM_TryForceReset()").strip(),
            "Return False",
        )

    def test_reset_acknowledgement_rejects_menu_and_registry_guards_before_mutation(self) -> None:
        reset = _function(self.manager, "Bool Function OpenMCM_TryForceReset()")
        before_lock = reset.split("_registryBusy = True", 1)[0]
        for condition in (
            "_registryBusy",
            "_menuOpen",
            'UI.IsMenuOpen(JOURNAL_MENU) || UI.IsMenuOpen("RaceSex Menu")',
        ):
            with self.subTest(condition=condition):
                self.assertRegex(
                    before_lock,
                    rf"(?s)If {re.escape(condition)}\s+Return False\s+EndIf",
                )
        self.assertNotIn("GotoState", before_lock)
        self.assertNotIn("InitializeStorage", before_lock)
        self.assertNotIn("SendModEvent", before_lock)
        self.assertNotIn("RegisterForSingleUpdate", reset)
        self.assertLess(before_lock.index("UI.IsMenuOpen"), before_lock.index("If _menuOpen"))
        self.assertLess(before_lock.index("If _menuOpen"), before_lock.index("If _registryBusy"))
        self.assertRegex(reset, r"(?s)If _registryBusy\s+Return False\s+EndIf\s+_registryBusy = True")

    def test_failed_reset_storage_validation_returns_false_without_announcing_reset(self) -> None:
        reset = _function(self.manager, "Bool Function OpenMCM_TryForceReset()")
        guard_start = reset.index("If !HasValidStorage()")
        guard_end = reset.index("EndIf", guard_start)
        guard = reset[guard_start:guard_end]
        self.assertIn("_registryBusy = False", guard)
        self.assertIn('GotoState("")', guard)
        self.assertIn("Return False", guard)
        self.assertNotIn("SendModEvent", reset[:guard_end])
        self.assertLess(reset.index("InitializeStorage()"), guard_start)

    def test_reset_acknowledges_only_after_complete_mutation_and_both_signals(self) -> None:
        reset = _function(self.manager, "Bool Function OpenMCM_TryForceReset()")
        reset_signal = reset.index('SendModEvent("SKICP_configManagerReset")')
        ready_signal = reset.index('SendModEvent("SKICP_configManagerReady")')
        success = reset.index("Return True")
        self.assertEqual(reset.count("Return True"), 1)
        self.assertEqual(reset.count('SendModEvent("SKICP_configManagerReset")'), 1)
        self.assertEqual(reset.count('SendModEvent("SKICP_configManagerReady")'), 1)
        self.assertRegex(
            reset,
            r'(?s)Int i = 0\s+While i < 128\s+_modConfigs\[i\] = None'
            r'\s+_modNames\[i\] = ""\s+i \+= 1\s+EndWhile',
        )
        for statement in (
            "_modConfigs[i] = None",
            '_modNames[i] = ""',
            "_activeConfig = None",
            "_curConfigID = 0",
            "_configCount = 0",
            "_addCounter = 0",
            "_storageRebuilt = False",
        ):
            with self.subTest(statement=statement):
                self.assertLess(reset.index(statement), reset_signal)
        completion = reset[reset_signal:]
        self.assertLess(completion.index("_registryBusy = False"), completion.index("PublishModList()"))
        self.assertLess(completion.index('GotoState("")'), completion.index("PublishModList()"))
        self.assertLess(reset_signal, ready_signal)
        self.assertLess(ready_signal, success)

    def test_acknowledged_reset_adds_no_saved_fields_and_preserves_version(self) -> None:
        declarations = re.sub(r";[^\r\n]*", "", self.manager.split("Int Function GetVersion", 1)[0])
        fields = re.findall(r"(?m)^([\w\[\]]+)\s+(_\w+)\b", declarations)
        self.assertEqual(fields, [
            ("SKI_ConfigBase[]", "_modConfigs"), ("String[]", "_modNames"),
            ("Int", "_curConfigID"), ("Int", "_configCount"),
            ("SKI_ConfigBase", "_activeConfig"), ("Bool", "_lockInit"),
            ("Bool", "_locked"), ("Bool", "_cleanupFlag"), ("Int", "_addCounter"),
            ("Int", "_updateCounter"), ("Bool", "_storageRebuilt"),
            ("Bool", "_menuOpen"), ("Bool", "_registryBusy"),
            ("Bool", "_openmcmAPIEnabled"), ("String", "_openmcmBrowserState"),
        ])
        self.assertEqual(_function(self.manager, "Int Function GetVersion()").strip(), "Return 4")

    def test_config_base_reload_uses_only_skyui_lifecycle_calls(self) -> None:
        reload_body = _event(self.base, "Event OnGameReload()")
        self.assertNotIn("IsRegisteredMod", reload_body)
        self.assertIn('RegisterForModEvent("SKICP_configManagerReady"', reload_body)
        self.assertIn('RegisterForModEvent("SKICP_configManagerReset"', reload_body)

    def test_ready_heartbeat_always_calls_original_registration_abi(self) -> None:
        ready = _event(
            self.base,
            "Event OnConfigManagerReady(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)",
        )
        self.assertNotIn("IsRegisteredMod", ready)
        self.assertNotIn("_configManager == candidate", ready)
        self.assertIn("candidate.RegisterMod(Self, ModName)", ready)
        self.assertLess(
            ready.index("previousManager = _configManager"),
            ready.index("candidate.RegisterMod(Self, ModName)"),
        )

    def test_ready_heartbeat_updates_cache_only_after_registration_succeeds(self) -> None:
        ready = _event(
            self.base,
            "Event OnConfigManagerReady(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)",
        )
        before_success, success = ready.split("If assignedID >= 0", maxsplit=1)
        self.assertNotIn("_configManager = candidate", before_success)
        self.assertNotIn("_configID = assignedID", before_success)
        self.assertIn("_configManager = candidate", success)
        self.assertIn("_configID = assignedID", success)

    def test_ready_heartbeat_suppresses_only_duplicate_callback(self) -> None:
        ready = _event(
            self.base,
            "Event OnConfigManagerReady(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)",
        )
        self.assertIn("previousManager != candidate || previousID != assignedID", ready)
        self.assertEqual(ready.count("OnConfigRegister()"), 1)

    def test_manager_duplicate_registration_does_not_increment_counters(self) -> None:
        register = _function(
            self.manager,
            "Int Function RegisterMod(SKI_ConfigBase a_menu, String a_modName)",
        )
        duplicate = register.split("If existingID >= 0", maxsplit=1)[1].split(
            "EndIf", maxsplit=1
        )[0]
        self.assertNotIn("_configCount +=", duplicate)
        self.assertNotIn("_addCounter +=", duplicate)
        self.assertIn("_modNames[existingID] = a_modName", duplicate)
        self.assertIn("Return existingID", duplicate)

    def test_registry_identity_lookups_do_not_run_scripted_slot_scans(self) -> None:
        for declaration in (
            "Int Function RegisterMod(SKI_ConfigBase a_menu, String a_modName)",
            "Int Function UnregisterMod(SKI_ConfigBase a_menu)",
        ):
            with self.subTest(declaration=declaration):
                body = _function(self.manager, declaration)
                self.assertEqual(body.count("_modConfigs.Find(a_menu)"), 1)
                self.assertNotRegex(body, r"(?im)^\s*While\b")
                self.assertLess(
                    body.index("If a_menu == None"),
                    body.index("_modConfigs.Find(a_menu)"),
                )
                self.assertLess(
                    body.index("_registryBusy = True"),
                    body.index("_modConfigs.Find(a_menu)"),
                )
                self.assertLess(
                    body.index("If !HasValidStorage()"),
                    body.index("_modConfigs.Find(a_menu)"),
                )

    def test_next_id_uses_native_find_with_wraparound_and_preserves_full_registry_cursor(self) -> None:
        next_id = _function(self.manager, "Int Function NextID()")
        self.assertNotRegex(next_id, r"(?im)^\s*While\b")
        self.assertLess(
            next_id.index("If !HasValidStorage()"),
            next_id.index("_modConfigs.Find(None, _curConfigID)"),
        )
        self.assertRegex(
            next_id,
            r"(?is)Int\s+next\s*=\s*_modConfigs\.Find\(None,\s*_curConfigID\)"
            r"\s*If\s+next\s*<\s*0\s*next\s*=\s*_modConfigs\.Find\(None\)\s*EndIf",
        )
        self.assertEqual(next_id.count("_curConfigID = next"), 1)
        self.assertRegex(
            next_id,
            r"(?is)If\s+next\s*>=\s*0\s*_curConfigID\s*=\s*next\s*EndIf",
        )
        self.assertIn("Return next", next_id)

    def test_unregister_none_cannot_consume_an_empty_registry_slot(self) -> None:
        unregister = _function(
            self.manager,
            "Int Function UnregisterMod(SKI_ConfigBase a_menu)",
        )
        self.assertIn("If a_menu == None", unregister)
        self.assertLess(unregister.index("If a_menu == None"), unregister.index("If _registryBusy"))
        none_guard = unregister.split("If a_menu == None", 1)[1].split("EndIf", 1)[0]
        self.assertIn("Return -1", none_guard)

    def test_storage_repair_normalizes_the_saved_next_slot(self) -> None:
        initialize = _function(self.manager, "Function InitializeStorage()")
        self.assertIn("If _curConfigID < 0 || _curConfigID >= 128", initialize)
        self.assertIn("_curConfigID = 0", initialize)
        self.assertLess(
            initialize.index("If _curConfigID < 0 || _curConfigID >= 128"),
            initialize.index("If !rebuildNames"),
        )

    def test_direct_option_updates_use_the_normalized_page_local_index(self) -> None:
        for declaration, buffer_name in (
            ("Function SetOptionStrValue(Int a_index, String a_strValue, Bool a_noUpdate)", "_strValueBuf"),
            ("Function SetOptionNumValue(Int a_index, Float a_numValue, Bool a_noUpdate)", "_numValueBuf"),
            (
                "Function SetOptionValues(Int a_index, String a_strValue, Float a_numValue, Bool a_noUpdate)",
                "_strValueBuf",
            ),
        ):
            with self.subTest(declaration=declaration):
                body = _function(self.base, declaration)
                self.assertIn("Int index = GetOptionIndex(a_index)", body)
                self.assertIn(f"{buffer_name}[index]", body)
                self.assertNotIn(f"{buffer_name}[a_index]", body)
                self.assertIn('MENU_ROOT + ".optionCursorIndex", index', body)


if __name__ == "__main__":
    unittest.main()
