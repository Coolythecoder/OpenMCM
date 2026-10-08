from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANAGER_PATH = REPOSITORY_ROOT / "src" / "papyrus" / "SKI_ConfigManager.psc"
PANEL_PATH = REPOSITORY_ROOT / "src" / "actionscript" / "MCMCompatPanel.as"


def _papyrus_event(source: str, declaration: str) -> str:
    match = re.search(
        rf"(?is){re.escape(declaration)}\s*(.*?)\bendEvent\b",
        source,
    )
    if not match:
        raise AssertionError(f"missing {declaration}")
    return match.group(1)


def _between(source: str, start: str, end: str) -> str:
    start_index = source.find(start)
    end_index = source.find(end, start_index + len(start))
    if start_index < 0 or end_index < 0:
        raise AssertionError(f"missing source range {start!r} -> {end!r}")
    return source[start_index:end_index]


def _papyrus_function(source: str, declaration: str) -> str:
    match = re.search(
        rf"(?is){re.escape(declaration)}\s*(.*?)\bendFunction\b",
        source,
    )
    if not match:
        raise AssertionError(f"missing {declaration}")
    return match.group(1)


class RegistrationHandshakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manager = MANAGER_PATH.read_text(encoding="utf-8")
        cls.panel = PANEL_PATH.read_text(encoding="utf-8")

    def test_manager_subscribes_to_panel_list_requests(self) -> None:
        reload_body = _papyrus_event(self.manager, "Event OnGameReload()")
        self.assertIn(
            'RegisterForModEvent("OPENMCM_modListRequested", "OnModListRequest")',
            reload_body,
        )

    def test_request_handler_republishes_authoritative_sparse_array(self) -> None:
        handler = _papyrus_event(
            self.manager,
            "Event OnModListRequest(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)",
        )
        self.assertIn("PublishModList()", handler)
        self.assertNotIn("GotoState", handler)

        publisher = _papyrus_function(self.manager, "Function PublishModList()")
        self.assertIn("InitializeStorage()", publisher)
        self.assertIn(
            'UI.InvokeStringA(JOURNAL_MENU, MENU_ROOT + ".setModNames", _modNames)',
            publisher,
        )

    def test_menu_open_publishes_once_without_delayed_retries(self) -> None:
        menu_open = _papyrus_event(self.manager, "Event OnMenuOpen(String a_menuName)")
        self.assertEqual(menu_open.count("PublishModList()"), 1)
        self.assertNotIn("Utility.Wait", menu_open)

    def test_closed_journal_does_not_queue_a_mod_list_or_repair_storage(self) -> None:
        publisher = _papyrus_function(self.manager, "Function PublishModList()")
        guard = _between(publisher, "If !UI.IsMenuOpen(JOURNAL_MENU)", "EndIf")
        self.assertIn("Return", guard)
        self.assertLess(
            publisher.index("If !UI.IsMenuOpen(JOURNAL_MENU)"),
            publisher.index("InitializeStorage()"),
        )
        self.assertLess(
            publisher.index("If !UI.IsMenuOpen(JOURNAL_MENU)"),
            publisher.index("UI.InvokeStringA("),
        )

    def test_successful_registration_immediately_publishes_the_list(self) -> None:
        register_mod = _papyrus_function(
            self.manager,
            "Int Function RegisterMod(SKI_ConfigBase a_menu, String a_modName)",
        )
        self.assertEqual(register_mod.count("PublishModList()"), 1)
        self.assertLess(
            register_mod.index("_addCounter += 1"),
            register_mod.rindex("PublishModList()"),
        )

    def test_duplicate_registration_does_not_replace_an_active_page(self) -> None:
        register_mod = _papyrus_function(
            self.manager,
            "Int Function RegisterMod(SKI_ConfigBase a_menu, String a_modName)",
        )
        duplicate = _between(
            register_mod,
            "If existingID >= 0",
            "EndIf",
        )
        self.assertNotIn("PublishModList()", duplicate)
        self.assertIn("Return existingID", duplicate)

    def test_registration_notification_does_not_republish_the_list(self) -> None:
        update = _papyrus_event(self.manager, "Event OnUpdate()")
        added_branch = _between(update, "If _addCounter > 0", "EndIf")
        self.assertNotIn("PublishModList()", update)
        self.assertIn("Debug.Notification(", added_branch)
        self.assertLess(
            added_branch.index("Debug.Notification("),
            added_branch.index("_addCounter = 0"),
        )

    def test_journal_close_does_not_start_an_extra_registration_wave(self) -> None:
        closed = _papyrus_event(self.manager, "Event OnMenuClose(String a_menuName)")
        self.assertNotIn("SendModEvent(", closed)
        self.assertNotIn("PublishModList()", closed)
        # Registration retries remain scheduled independently of Journal use.
        update = _papyrus_event(self.manager, "Event OnUpdate()")
        self.assertIn('SendModEvent("SKICP_configManagerReady")', update)
        self.assertIn("RegisterForSingleUpdate(5.0)", update)
        self.assertIn("RegisterForSingleUpdate(30.0)", update)

    def test_visible_initialized_panel_requests_fresh_list(self) -> None:
        start_page = _between(
            self.panel,
            "public function startPage():Void",
            "public function endPage():Void",
        )
        self.assertIn("_beginModListRequest();", start_page)
        self.assertLess(
            start_page.index("_active = true;"),
            start_page.index("_beginModListRequest();"),
        )
        self.assertLess(
            start_page.index("_visible = true;"),
            start_page.index("_beginModListRequest();"),
        )
        self.assertLess(
            start_page.index("_renderSide();"),
            start_page.index("_beginModListRequest();"),
        )

        request = _between(
            self.panel,
            "private function _requestModList():Void",
            "private function _stopModListRequest():Void",
        )
        self.assertIn(
            'MCMCompatUtil.sendModEvent("SKICP_modSelected", null, -1);',
            request,
        )
        self.assertIn("_modListRequestAttempts >= 20", request)

    def test_existing_selection_event_handles_saved_game_refresh_sentinel(self) -> None:
        select = _papyrus_event(
            self.manager,
            "Event OnModSelect(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)",
        )
        sentinel = _between(select, "If index < 0", "EndIf")
        self.assertIn("PublishModList()", sentinel)
        # A queued refresh must never unlock a later real page request.
        self.assertNotIn("UnlockPanel()", sentinel)
        self.assertIn("Return", sentinel)
        self.assertLess(select.index("If index < 0"), select.index("IsRegisteredIndex(index)"))

    def test_set_mod_names_acknowledges_and_stops_retries(self) -> None:
        setter = _between(
            self.panel,
            "public function setModNames():Void",
            "public function setPageNames():Void",
        )
        self.assertIn("_stopModListRequest();", setter)

    def test_late_mod_list_refresh_preserves_active_mcm_page(self) -> None:
        setter = _between(
            self.panel,
            "public function setModNames():Void",
            "public function setPageNames():Void",
        )
        preserve = _between(setter, 'if (_sideMode == "pages")', "return;")
        self.assertNotIn("_optionEntries = [];", preserve)
        self.assertLess(
            setter.index('if (_sideMode == "pages")'),
            setter.index("_optionEntries = [];"),
        )

    def test_opening_panel_starts_from_authoritative_mod_list(self) -> None:
        start_page = _between(
            self.panel,
            "public function startPage():Void",
            "public function endPage():Void",
        )
        self.assertIn('_sideMode = "mods";', start_page)
        self.assertIn("_sideItems = _modNames;", start_page)
        self.assertIn("_pageNames = [];", start_page)
        self.assertIn("_optionEntries = [];", start_page)
        self.assertLess(
            start_page.index('_sideMode = "mods";'),
            start_page.index("_beginModListRequest();"),
        )

    def test_page_sublist_waits_for_explicit_selection_like_skyui(self) -> None:
        setter = _between(
            self.panel,
            "public function setPageNames():Void",
            "public function setCustomContentParams",
        )
        self.assertIn("_sideIndex = -1;", setter)
        self.assertNotIn("_pageNames.length > 0 ? 0 : -1", setter)


if __name__ == "__main__":
    unittest.main()
