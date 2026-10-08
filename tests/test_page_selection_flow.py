from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = REPOSITORY_ROOT / "src" / "actionscript" / "MCMCompatPanel.as"
BASE_PATH = REPOSITORY_ROOT / "src" / "papyrus" / "SKI_ConfigBase.psc"
MANAGER_PATH = REPOSITORY_ROOT / "src" / "papyrus" / "SKI_ConfigManager.psc"


def _between(source: str, start: str, end: str) -> str:
    start_index = source.find(start)
    end_index = source.find(end, start_index + len(start))
    if start_index < 0 or end_index < 0:
        raise AssertionError(f"missing source range {start!r} -> {end!r}")
    return source[start_index:end_index]


def _papyrus_body(source: str, declaration: str, terminator: str) -> str:
    match = re.search(
        rf"(?is){re.escape(declaration)}\s*(.*?)\b{terminator}\b",
        source,
    )
    if not match:
        raise AssertionError(f"missing {declaration}")
    return match.group(1)


class PageSelectionFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.panel = PANEL_PATH.read_text(encoding="utf-8")
        cls.base = BASE_PATH.read_text(encoding="utf-8")
        cls.manager = MANAGER_PATH.read_text(encoding="utf-8")

    def test_open_config_matches_skyui_page_publication_order(self) -> None:
        body = _papyrus_body(self.base, "Function OpenConfig()", "EndFunction")
        self.assertLess(body.index("AllocateOptionBuffers()"), body.index('SetPage("", -1)'))
        self.assertLess(body.index('SetPage("", -1)'), body.index("OnConfigOpen()"))
        self.assertLess(body.index("OnConfigOpen()"), body.index(".setPageNames"))

    def test_mod_click_enters_page_mode_and_sends_original_registry_index(self) -> None:
        body = _between(
            self.panel,
            "private function _selectMod(entry:Object):Void",
            "private function _selectPage(entry:Object):Void",
        )
        event = 'MCMCompatUtil.sendModEvent("SKICP_modSelected", null, entry.modIndex);'
        self.assertIn(event, body)
        self.assertLess(body.index('_sideMode = "pages";'), body.index(event))
        self.assertLess(body.index("_state = WAIT_FOR_OPTION_DATA;"), body.index(event))

    def test_page_names_keep_raw_tokens_blank_entries_and_original_indices(self) -> None:
        body = _between(
            self.panel,
            "public function setPageNames():Void",
            "public function setCustomContentParams",
        )
        self.assertIn('if (raw.toLowerCase() != "none")', body)
        self.assertNotIn('raw != ""', body)
        self.assertIn("pageIndex:i, pageName:raw", body)
        self.assertIn("text:MCMCompatUtil.translate(raw)", body)
        self.assertIn("_sideIndex = -1;", body)
        self.assertNotIn("_selectFirstOption();", body)

    def test_page_click_sends_raw_token_and_original_page_index(self) -> None:
        body = _between(
            self.panel,
            "private function _selectPage(entry:Object):Void",
            "private function _selectActivePage():Void",
        )
        event = (
            'MCMCompatUtil.sendModEvent("SKICP_pageSelected", entry.pageName,\n'
            "\t\t\tentry.pageIndex);"
        )
        self.assertIn(event, body)
        self.assertIn("if (_pageNames[i] == entry) _activePageIndex = i;", body)
        self.assertLess(body.index("_activePageIndex = i;"), body.index(event))
        self.assertLess(body.index("_state = WAIT_FOR_OPTION_DATA;"), body.index(event))

    def test_manager_opens_mod_and_page_before_unlocking_panel(self) -> None:
        mod_select = _papyrus_body(
            self.manager,
            "Event OnModSelect(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)",
            "EndEvent",
        )
        self.assertLess(mod_select.index("_activeConfig.OpenConfig()"), mod_select.rindex("UnlockPanel()"))

        page_select = _papyrus_body(
            self.manager,
            "Event OnPageSelect(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)",
            "EndEvent",
        )
        self.assertIn("_activeConfig.SetPage(a_strArg, a_numArg as Int)", page_select)
        self.assertLess(page_select.index("_activeConfig.SetPage"), page_select.index("UnlockPanel()"))

    def test_zero_option_page_still_flushes_and_renders(self) -> None:
        body = _between(
            self.panel,
            "public function flushOptionBuffers(optionCount:Number):Void",
            "private function _getOptionCursor():Object",
        )
        self.assertIn("Math.max(0", body)
        self.assertIn("_applyTitleText();", body)
        self.assertIn("_applyInfoText();", body)
        self.assertIn("_renderOptions();", body)
        self.assertNotIn("if (count == 0)", body)

    def test_only_top_level_mod_list_uses_the_welcome_splash(self) -> None:
        render = _between(
            self.panel,
            "private function _renderOptions():Void",
            "private function _drawOptionGlyph",
        )
        self.assertIn("if (_welcomeVisible)", render)
        self.assertIn("_renderWelcomeMark(_welcomeLayer);", render)

        select_mod = _between(
            self.panel,
            "private function _selectMod(entry:Object):Void",
            "private function _selectPage(entry:Object):Void",
        )
        self.assertIn("_welcomeVisible = false;", select_mod)
        self.assertLess(
            select_mod.index("_welcomeVisible = false;"),
            select_mod.index("unloadCustomContent();"),
        )

        welcome = _between(
            self.panel,
            "public function showWelcomeScreen():Void",
            "private function _isVisibleAndActive",
        )
        self.assertIn("_welcomeVisible = true;", welcome)

    def test_provider_custom_content_replaces_the_welcome_splash(self) -> None:
        loader = _between(
            self.panel,
            "public function loadCustomContent(source:String):Void",
            "public function unloadCustomContent():Void",
        )
        self.assertIn("_welcomeVisible = false;", loader)
        self.assertLess(
            loader.index("_welcomeVisible = false;"),
            loader.index("unloadCustomContent();"),
        )

    def test_page_navigation_precedes_single_row_navigation(self) -> None:
        navigation = _between(
            self.panel,
            "private function _handleNavigation",
            "private function _activateCurrent",
        )
        self.assertLess(navigation.index('nav.indexOf("pageup")'), navigation.index('nav.indexOf("up")'))
        self.assertLess(navigation.index('nav.indexOf("pagedown")'), navigation.index('nav.indexOf("down")'))
        self.assertIn("_pageFocusedList(-1);", navigation)
        self.assertIn("_pageFocusedList(1);", navigation)

    def test_skyui_list_navigation_stops_at_boundaries(self) -> None:
        side = _between(
            self.panel,
            "private function _moveSide",
            "private function _setSideSelection",
        )
        self.assertIn("if (candidate < 0 || candidate >= _sideItems.length)", side)
        self.assertNotIn("_sideItems.length - 1;", side.split("} else {", 1)[1])
        self.assertNotIn("_sideIndex = 0;", side)

        options = _between(
            self.panel,
            "private function _moveOption",
            "private function _setOptionSelection",
        )
        self.assertIn("if (candidate < 0 || candidate >= _optionEntries.length)", options)
        self.assertNotIn("_isOptionSelectable(candidate)", options)
        self.assertNotIn("candidate = delta > 0 ? 0", options)

    def test_wheel_scrolls_the_pointed_list_without_moving_selection(self) -> None:
        wheel = _between(
            self.panel,
            "public function onMouseWheel",
            "private function _isPointerInside",
        )
        self.assertIn("_scrollSideList", wheel)
        self.assertIn("_scrollOptionsList", wheel)
        self.assertNotIn("_moveSide", wheel)
        self.assertNotIn("_moveOption", wheel)

        side_scroll = _between(
            self.panel,
            "private function _scrollSideList",
            "private function _scrollOptionsList",
        )
        option_scroll = _between(
            self.panel,
            "private function _scrollOptionsList",
            "private function _moveSide",
        )
        self.assertNotIn("_sideIndex =", side_scroll)
        self.assertNotIn("_optionIndex =", option_scroll)

    def test_option_keyboard_navigation_keeps_physical_slots(self) -> None:
        selection = _between(
            self.panel,
            "private function _setOptionSelection",
            "private function _pressOption",
        )
        self.assertNotIn("_isOptionSelectable", selection)
        self.assertIn("_initHighlight(index);", selection)

        select_option = _between(
            self.panel,
            "private function _selectOption",
            "private function _startRemap",
        )
        self.assertIn("entry.flags & FLAG_DISABLED", select_option)
        self.assertNotIn("FLAG_HIDDEN", select_option)

    def test_mouse_rollout_clears_transient_list_selection(self) -> None:
        side = _between(
            self.panel,
            "private function _renderSide",
            "private function _renderOptions",
        )
        options = _between(
            self.panel,
            "private function _renderOptions",
            "private function _drawOptionGlyph",
        )
        self.assertIn("list.getRenderer(", side)
        self.assertIn("_optionsList.getRenderer(", options)
        component = (REPOSITORY_ROOT / "src/actionscript/MCMCompatList.as").read_text(encoding="utf-8")
        self.assertIn("row.onRollOut = function():Void", component)
        self.assertIn("this._list.onItemRollOut(this.itemIndex);", component)
        self.assertIn("if (isAutoUnselect && index == _selectedIndex)", component)
        self.assertIn("selectIndex(-1, true);", component)

    def test_page_title_is_a_mouse_back_target_and_back_restores_mod(self) -> None:
        side = _between(
            self.panel,
            "private function _renderSide",
            "private function _renderOptions",
        )
        self.assertIn('createEmptyMovieClip("titleBack", 1000)', side)
        self.assertIn("this._owner._goBack();", side)

        back = _between(
            self.panel,
            "private function _goBack",
            "private function _selectMod",
        )
        self.assertIn("_findModListIndex(_selectedModRegistryIndex)", back)

    def test_footer_is_blank_for_no_or_noninteractive_option_selection(self) -> None:
        footer = _between(
            self.panel,
            "private function _updateFooter",
            "public function showWelcomeScreen",
        )
        self.assertIn("_optionIndex < 0", footer)
        self.assertIn("entry.optionType == OPTION_EMPTY", footer)
        self.assertIn("entry.optionType == OPTION_HEADER", footer)
        self.assertIn("FLAG_DISABLED | FLAG_HIDDEN", footer)

    def test_state_option_cannot_replace_an_occupied_slot(self) -> None:
        body = _papyrus_body(
            self.base,
            "Function AddOptionST(String a_stateName, Int a_optionType, String a_text, String a_strValue, Float a_numValue, Int a_flags)",
            "EndFunction",
        )
        self.assertIn('If _stateOptionMap[index] != ""', body)
        self.assertIn('Error("State option index " + index + " already in use")', body)
        self.assertLess(body.index('If _stateOptionMap[index] != ""'), body.index("_stateOptionMap[index] = a_stateName"))


if __name__ == "__main__":
    unittest.main()
