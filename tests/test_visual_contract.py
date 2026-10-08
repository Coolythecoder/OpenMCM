from __future__ import annotations

import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = REPOSITORY_ROOT / "src" / "actionscript" / "MCMCompatPanel.as"
UTIL_PATH = REPOSITORY_ROOT / "src" / "actionscript" / "MCMCompatUtil.as"
LIST_PATH = REPOSITORY_ROOT / "src" / "actionscript" / "MCMCompatList.as"


def _constant(source: str, name: str) -> float:
    match = re.search(
        rf"private\s+static\s+var\s+{re.escape(name)}:Number\s*=\s*([0-9.]+)\s*;",
        source,
    )
    if not match:
        raise AssertionError(f"missing visual constant {name}")
    return float(match.group(1))


class SkyUI6VisualContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.panel = PANEL_PATH.read_text(encoding="utf-8")
        cls.util = UTIL_PATH.read_text(encoding="utf-8")
        cls.list_component = LIST_PATH.read_text(encoding="utf-8")

    def test_classic_stage_geometry_is_pinned(self) -> None:
        expected = {
            "FRAME_X": 82,
            "FRAME_Y": 70,
            "FRAME_W": 1116,
            "FRAME_H": 506,
            "DIVIDER_X": 330,
            "SIDE_X": 168,
            "SIDE_Y": 108,
            "SIDE_W": 162,
            "SIDE_ROW_H": 24,
            "SIDE_VISIBLE_ROWS": 18,
            "PAGE_SIDE_Y": 145,
            "PAGE_VISIBLE_ROWS": 17,
            "OPTIONS_PANEL_X": 345,
            "OPTIONS_PANEL_Y": 100,
            "OPTIONS_X": 352,
            "OPTIONS_Y": 131,
            "OPTION_W": 380,
            "OPTION_GAP": 40,
            "OPTION_ROW_H": 33,
            "OPTION_VISIBLE_ROWS": 12,
            "INFO_X": 377,
            "INFO_Y": 568,
            "TITLE_CENTER_X": 721,
			"WELCOME_CENTER_X": 723,
			"WELCOME_CENTER_Y": 287,
            "FOOTER_BASE_Y": 670,
            "DIALOG_X": 518.5,
            "DIALOG_W": 401,
        }
        for name, value in expected.items():
            with self.subTest(name=name):
                self.assertEqual(_constant(self.panel, name), value)

    def test_custom_content_uses_options_panel_coordinate_space(self) -> None:
        self.assertIn(
            "_customContent._x = OPTIONS_PANEL_X + _customContentX;", self.panel
        )
        self.assertIn(
            "_customContent._y = OPTIONS_PANEL_Y + _customContentY;", self.panel
        )
        self.assertNotIn("_customContent._x = OPTIONS_X +", self.panel)
        self.assertNotIn("_customContent._y = OPTIONS_Y +", self.panel)

    def test_ui_uses_localized_game_font_roles(self) -> None:
        for alias in (
            "$EverywhereFont",
            "$EverywhereMediumFont",
            "$EverywhereBoldFont",
        ):
            self.assertIn(alias, self.panel + self.util)
        self.assertIn("field.embedFonts = true;", self.util)
        self.assertIn("_inputField.embedFonts = true;", self.panel)
        self.assertIn(
            "format.letterSpacing = isNaN(letterSpacing) ? 0.8 : letterSpacing;",
            self.util,
        )
        self.assertIn("format.kerning = kerning == true;", self.util)
        self.assertIn('alias == "$EverywhereBoldFont"', self.util)

    def test_old_blue_card_and_fullscreen_modal_scrim_are_gone(self) -> None:
        for old_color in (
            "0x06090D",
            "0x101923",
            "0x182633",
            "0x416C84",
            "0x315B73",
            "0x78C5E8",
        ):
            self.assertNotIn(old_color, self.panel)
        self.assertNotRegex(
            self.panel,
            r"drawRect\(_modalLayer,\s*0,\s*0,\s*1280,\s*720",
        )

    def test_skyui_color_contract_is_two_by_fourteen(self) -> None:
        palette_match = re.search(
            r"private function _buildColorPalette\(\):Array\s*\{.*?return \[(.*?)\];",
            self.panel,
            re.DOTALL,
        )
        self.assertIsNotNone(palette_match)
        colors = re.findall(r"0x[0-9A-Fa-f]{6}", palette_match.group(1))
        self.assertEqual(len(colors), 28)
        self.assertIn("var column:Number = i % 14;", self.panel)
        self.assertIn("var line:Number = Math.floor(i / 14);", self.panel)
        self.assertIn("var size:Number = selected ? 37.5 : 25;", self.panel)

    def test_focus_active_page_and_compact_dialog_states_are_separate(self) -> None:
        self.assertIn("private var _activePageIndex:Number;", self.panel)
        self.assertIn('var selected:Boolean = i == _optionIndex && _focus == FOCUS_OPTIONS;', self.panel)
        self.assertIn("_setContentDimmed(true);", self.panel)
        self.assertIn("_setContentDimmed(false);", self.panel)
        self.assertIn("dialogHeight = 146;", self.panel)
        self.assertIn("messageProbe.textHeight", self.panel)

    def test_footer_chrome_moves_with_safe_area_prompts(self) -> None:
        self.assertIn('createEmptyMovieClip("footerDecor", 4)', self.panel)
        self.assertIn("_footerDecor._y = footerY;", self.panel)
        self.assertIn(
            "footerY = FOOTER_BASE_Y + Number(safe.y) - 8;", self.panel
        )
        self.assertIn("_footerLeftField._y = footerY + 22;", self.panel)
        self.assertIn("_footerRightField._y = footerY + 22;", self.panel)
        self.assertNotRegex(
            self.panel,
            r"Math\.max\(620,\s*Math\.min\(688,\s*footerY\)\)",
        )
        self.assertIn("0, 0, 1280, 58", self.panel)
        self.assertIn("0x000000, 60", self.panel)

    def test_main_panel_uses_reference_translucency(self) -> None:
        self.assertIn(
            "FRAME_H, 0x000000, 80, 0x999999, 80", self.panel
        )

    def test_ultrawide_keeps_reference_aspect_ratio(self) -> None:
        init_start = self.panel.index("public function initExtensions():Void")
        init_end = self.panel.index("public function setPlatform", init_start)
        init_body = self.panel[init_start:init_end]
        self.assertIn('Stage.scaleMode = "showAll";', init_body)
        self.assertLess(
            init_body.index('Stage.scaleMode = "showAll";'),
            init_body.index("showWelcomeScreen();"),
        )

    def test_welcome_has_no_options_divider_or_duplicate_info_trapezoid(self) -> None:
        build_start = self.panel.index("private function _buildChrome():Void")
        build_end = self.panel.index("private function _drawFrameOrnaments", build_start)
        build_body = self.panel[build_start:build_end]
        self.assertNotIn("752, OPTIONS_Y - 8", build_body)

        render_start = self.panel.index("private function _renderOptions():Void")
        render_end = self.panel.index("private function _drawOptionGlyph", render_start)
        render_body = self.panel[render_start:render_end]
        empty_return = render_body.index("_renderWelcomeMark(_welcomeLayer);")
        divider = render_body.index("752, 101, 752, 547")
        self.assertLess(empty_return, divider)

        ornaments_start = self.panel.index("private function _drawFrameOrnaments")
        ornaments_end = self.panel.index("private function _drawCornerOrnament", ornaments_start)
        ornaments = self.panel[ornaments_start:ornaments_end]
        self.assertNotIn("x:394", ornaments)
        self.assertNotIn("x:1047", ornaments)

    def test_empty_lists_match_skyui_blank_panes(self) -> None:
        side_start = self.panel.index("private function _renderSide():Void")
        side_end = self.panel.index("private function _renderOptions():Void", side_start)
        side_body = self.panel[side_start:side_end]
        self.assertNotIn("Waiting for registered configuration menus", side_body)
        self.assertNotIn("No page list", side_body)
        empty_branch = side_body.split(
            "if (_sideItems.length == 0) {", maxsplit=1
        )[1].split("}", maxsplit=1)[0]
        self.assertIn('MCMCompatUtil.applyText(_sideScrollField, "");', empty_branch)
        self.assertIn("return;", empty_branch)

    def test_option_fields_use_skyui_authored_offsets_and_right_edge(self) -> None:
        option_start = self.panel.index("private function _renderOptions():Void")
        option_end = self.panel.index("private function _drawScrollIndicator", option_start)
        option_body = self.panel[option_start:option_end]
        self.assertIn("x + 12, y + 3, OPTION_W, 30.5, 22", option_body)
        self.assertIn("x + 2, y + 3, OPTION_W, 31.7, 20", option_body)
        self.assertIn("x + 2, y + 3, OPTION_W, 31.4, 22", option_body)
        self.assertIn("labelFormat.leading = 2;", option_body)
        self.assertIn("valueFormat.leading = 2;", option_body)
        self.assertIn("var rightEdge:Number = x + OPTION_W;", option_body)
        self.assertIn("x + OPTION_W - 23, y + 4, 23, 23", option_body)
        self.assertNotIn("x + 262", option_body)

    def test_side_list_text_and_selection_stop_at_the_divider(self) -> None:
        side_start = self.panel.index("private function _renderSide():Void")
        side_end = self.panel.index("private function _renderOptions():Void", side_start)
        side_body = self.panel[side_start:side_end]
        self.assertIn('var labelWidth:Number = _sideMode == "pages" ? 155 : 158;', side_body)
        self.assertIn("SIDE_X + 2, labelY, labelWidth, labelHeight", side_body)
        self.assertIn('var labelY:Number = y + (_sideMode == "pages" ? 2 : 2.5);', side_body)
        self.assertIn('var labelHeight:Number = _sideMode == "pages" ? 24 : 27;', side_body)
        self.assertIn('SIDE_X + 2 : SIDE_X - 47;', side_body)
        self.assertIn("DIVIDER_X - selectedLeft, SIDE_ROW_H", side_body)
        self.assertNotIn("SIDE_X + SIDE_W + 10", side_body)
        self.assertIn("drawHorizontalGradientRect", side_body)
        self.assertIn("new flash.geom.Matrix();", self.util)

    def test_mouse_rows_have_stable_full_width_press_targets(self) -> None:
        side_start = self.panel.index("private function _renderSide():Void")
        side_end = self.panel.index("private function _renderOptions():Void", side_start)
        side_body = self.panel[side_start:side_end]
        self.assertIn('createEmptyMovieClip("triggerArea", 0)', side_body)
        self.assertIn("DIVIDER_X - FRAME_X - 9", side_body)
        self.assertIn("getRenderer(", side_body)
        self.assertNotIn("_sideRows.removeMovieClip()", side_body)
        self.assertNotIn("row.hitArea = trigger;", side_body)
        self.assertNotIn("trigger._visible = false;", side_body)
        self.assertIn("trigger._visible = true;", side_body)
        self.assertIn("trigger._alpha = 0;", side_body)
        self.assertRegex(side_body, r"drawRect\(trigger, FRAME_X \+ 9, y,\s*"
                         r"DIVIDER_X - FRAME_X - 9, SIDE_ROW_H, 0x000000, 100,")
        self.assertNotIn("row.onPress", side_body)
        self.assertNotIn("row.onRelease", side_body)

        option_start = side_end
        option_end = self.panel.index("private function _drawOptionGlyph", option_start)
        option_body = self.panel[option_start:option_end]
        self.assertIn('createEmptyMovieClip("triggerArea", 0)', option_body)
        self.assertIn("getRenderer(", option_body)
        self.assertNotIn("_optionRows.removeMovieClip()", option_body)
        self.assertNotIn("row.hitArea = trigger;", option_body)
        self.assertNotIn("trigger._visible = false;", option_body)
        self.assertIn("trigger._visible = true;", option_body)
        self.assertIn("trigger._alpha = 0;", option_body)
        self.assertRegex(option_body, r"drawRect\(trigger, x - 7, y,\s*"
                         r"OPTION_W \+ 7, OPTION_ROW_H, 0x000000, 100,")
        self.assertNotIn("row.onPress", option_body)
        self.assertNotIn("row.onRelease", option_body)

        # Native handlers belong to the pooled renderer, not to a repaint of
        # the panel. List behavior and event dispatch have separate tests.
        self.assertIn("var row:MovieClip = _rows[slot];", self.list_component)
        self.assertIn("if (row == undefined) {", self.list_component)
        self.assertIn("row.onRollOver = function():Void", self.list_component)
        self.assertIn("row.onPress = function(", self.list_component)
        self.assertIn("this._list.pressIndex(this.itemIndex,", self.list_component)
        self.assertNotIn("row.onRelease", self.list_component)

        menu_start = self.panel.index("private function _renderMenuDialog():Void")
        menu_end = self.panel.index("private function _renderColorDialog():Void", menu_start)
        menu_body = self.panel[menu_start:menu_end]
        self.assertIn('createEmptyMovieClip("triggerArea", 0)', menu_body)
        self.assertIn("_menuDialogList.getRenderer(", menu_body)
        self.assertIn("_menuDialogList.beginUpdate();", menu_body)
        self.assertIn("_menuDialogList.endUpdate();", menu_body)
        self.assertIn("trigger._visible = true;", menu_body)
        self.assertIn("trigger._alpha = 0;", menu_body)
        self.assertRegex(menu_body, r"drawRect\(trigger, 547, y,\s*"
                         r"344, 24, 0x000000, 100, 0x000000, 0\);")
        self.assertNotIn("row.hitArea = trigger;", menu_body)
        self.assertNotIn("trigger._visible = false;", menu_body)
        self.assertNotIn("row.onPress", menu_body)
        self.assertNotIn("row.onRelease", menu_body)

    def test_welcome_and_title_share_the_reference_axis(self) -> None:
        welcome_start = self.panel.index("private function _renderWelcomeMark")
        welcome_end = self.panel.index("private function _optionActionLabel", welcome_start)
        welcome = self.panel[welcome_start:welcome_end]
        self.assertIn("var centerX:Number = WELCOME_CENTER_X;", welcome)
        self.assertIn("var centerY:Number = WELCOME_CENTER_Y;", welcome)
        self.assertLessEqual(
            abs(_constant(self.panel, "WELCOME_CENTER_X") -
                _constant(self.panel, "TITLE_CENTER_X")),
            2,
        )

        title_start = self.panel.index("private function _redrawTitlePlate")
        title_end = self.panel.index("private function _redrawInfoPlate", title_start)
        title = self.panel[title_start:title_end]
        self.assertIn("{x:left + 31.70, y:52}", title)
        self.assertIn("{x:right - 31.70, y:98}", title)
        self.assertIn("left + 42, 56.2", title)
        self.assertIn("], 0x000000, 100, 0x999999, 100, 1);", title)
        self.assertNotIn("_titleField._x =", title)
        self.assertNotIn("_titleField._width =", title)
        self.assertIn('358, 61, 730, 34, 24', self.panel)

    def test_distribution_does_not_load_skyui_visual_assets(self) -> None:
        self.assertNotRegex(self.panel, r'loadMovie\(\s*["\']skyui[/\\]')
        for linkage in (
            "OptionsListEntry",
            "ModListPanel",
            "OptionSliderDialog",
            "OptionMenuDialog",
            "OptionColorDialog",
        ):
            self.assertNotRegex(
                self.panel,
                rf'attachMovie\(\s*["\']{re.escape(linkage)}["\']',
            )


if __name__ == "__main__":
    unittest.main()
