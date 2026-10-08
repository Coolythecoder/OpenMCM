from __future__ import annotations

import re
import json
import shutil
import subprocess
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_PATH = REPOSITORY_ROOT / "src" / "actionscript" / "MCMCompatBootstrap.as"
PATCH_PATH = REPOSITORY_ROOT / "scripts" / "Patch-Journal.ps1"


def _brace_block(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        raise AssertionError(f"missing source marker {marker!r}")
    opening = source.find("{", start + len(marker))
    if opening < 0:
        raise AssertionError(f"missing opening brace after {marker!r}")

    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"unterminated source block after {marker!r}")


def _here_string(source: str, variable: str) -> str:
    match = re.search(
        rf"(?ms)^\${re.escape(variable)}\s*=\s*@'\r?\n(.*?)\r?\n'@",
        source,
    )
    if not match:
        raise AssertionError(f"missing PowerShell here-string ${variable}")
    return match.group(1)


def _assert_order(test: unittest.TestCase, source: str, *tokens: str) -> None:
    position = -1
    for token in tokens:
        next_position = source.find(token, position + 1)
        test.assertGreater(
            next_position,
            position,
            f"{token!r} is missing or out of lifecycle order",
        )
        position = next_position


class SkyUIJournalLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bootstrap = BOOTSTRAP_PATH.read_text(encoding="utf-8")
        cls.patch = PATCH_PATH.read_text(encoding="utf-8")
        cls.host = _here_string(cls.patch, "hostMethods")
        cls.mcm_branch = _here_string(cls.patch, "mcmBranch")

    def test_patched_open_uses_skyui_focus_and_start_order(self) -> None:
        body = _brace_block(self.host, "function ConfigPanelOpen()")
        _assert_order(
            self,
            body,
            "this.DisableTabs(true);",
            "this.SystemFader.Page_mc.endPage();",
            "this.DoHideMenu();",
            "_root.ConfigPanelFader._visible = true;",
            "MCMCompatBootstrap.raisePanel();",
            "gfx.managers.FocusHandler.instance.setFocus(this.ConfigPanel,0);",
            'MCMCompatBootstrap.playSound("UIMenuOK");',
            "this.ConfigPanel.startPage();",
        )
        self.assertNotIn("this.QuestsTab.disabled", body)

    def test_patched_close_uses_skyui_restore_order(self) -> None:
        body = _brace_block(self.host, "function ConfigPanelClose()")
        _assert_order(
            self,
            body,
            'MCMCompatBootstrap.playSound("UIMenuCancel");',
            "this.ConfigPanel.endPage();",
            "_root.ConfigPanelFader._visible = false;",
            "gfx.managers.FocusHandler.instance.setFocus(this,0);",
            "this.DoShowMenu();",
            "this.SystemFader.Page_mc.startPage();",
            "this.DisableTabs(false);",
        )

    def test_disable_tabs_matches_skyui_single_host_method(self) -> None:
        body = _brace_block(self.host, "function DisableTabs(abEnable)")
        for tab in ("QuestsTab", "StatsTab", "SystemTab"):
            self.assertIn(f"this.{tab}.disabled = abEnable;", body)

    def test_system_page_places_mcm_between_settings_and_controls(self) -> None:
        self.assertIn(
            "-Needle '      this.CategoryList.entryList.push({text:\"$SETTINGS\"});'",
            self.patch,
        )
        replacement = (
            'this.CategoryList.entryList.push({text:`"`$SETTINGS`"});`n'
            '      this.CategoryList.entryList.push({text:`"`$MOD CONFIGURATION`"});'
        )
        self.assertIn(replacement, self.patch)
        self.assertNotIn(
            "-Needle '      this.CategoryList.entryList.push({text:\"$QUIT\"});'",
            self.patch,
        )

    def test_system_page_delegates_single_open_sound_to_host(self) -> None:
        self.assertNotIn('PlaySound",["UIMenuOK"]', self.mcm_branch)
        _assert_order(
            self,
            self.mcm_branch,
            "_root.QuestJournalFader.Menu_mc.ConfigPanelOpen();",
            "this.CategoryList.setInteractive(true);",
            "return;",
        )

    def test_inserted_category_keeps_vanilla_action_indices(self) -> None:
        self.assertIn(
            'event.entry.text == "$CONTROLS" || event.entry.text == "$HELP" || '
            'event.entry.text == "$QUIT"',
            self.patch,
        )
        self.assertIn("_loc3_ -= 1;", self.patch)
        self.assertIn("-Needle '            _loc3_ = event.index + 1;'", self.patch)
        self.assertIn("-Replacement '            _loc3_ += 1;'", self.patch)

    def test_inserted_category_keeps_permission_indices_on_quit_controls_and_help(self) -> None:
        for original, shifted in (
            ("entryList[5],this.CategoryList.entryList[8],true", "entryList[5],this.CategoryList.entryList[9],true"),
            ("entryList[4],this.CategoryList.entryList[7],true", "entryList[4],this.CategoryList.entryList[8],true"),
            ("entryList[5],this.CategoryList.entryList[8],false", "entryList[5],this.CategoryList.entryList[9],false"),
            ("entryList[4],this.CategoryList.entryList[7],false", "entryList[4],this.CategoryList.entryList[8],false"),
        ):
            with self.subTest(original=original):
                self.assertIn(f"-Needle 'this.CategoryList.{original}'", self.patch)
                self.assertIn(f"-Replacement 'this.CategoryList.{shifted}'", self.patch)

        self.assertIn(
            'this.CategoryList.entryList[7].disabled = false;`n'
            '         this.CategoryList.entryList[8].disabled = false;',
            self.patch,
        )
        self.assertIn(
            'this.CategoryList.entryList[6].disabled = false;`n'
            '         this.CategoryList.entryList[7].disabled = false;',
            self.patch,
        )

    def test_runtime_fallback_open_keeps_the_same_order(self) -> None:
        body = _brace_block(
            self.bootstrap, "journal.ConfigPanelOpen = function():Void"
        )
        _assert_order(
            self,
            body,
            "this.DisableTabs(true);",
            "this.SystemFader.Page_mc.endPage();",
            "this.DoHideMenu();",
            "_root.ConfigPanelFader._visible = true;",
            "MCMCompatBootstrap.raisePanel();",
            "setFocus(this.ConfigPanel, 0);",
            'MCMCompatBootstrap.playSound("UIMenuOK");',
            "this.ConfigPanel.startPage();",
        )

    def test_runtime_fallback_close_keeps_the_same_order(self) -> None:
        body = _brace_block(
            self.bootstrap, "journal.ConfigPanelClose = function():Void"
        )
        _assert_order(
            self,
            body,
            'MCMCompatBootstrap.playSound("UIMenuCancel");',
            "this.ConfigPanel.endPage();",
            "_root.ConfigPanelFader._visible = false;",
            "setFocus(this, 0);",
            "this.DoShowMenu();",
            "this.SystemFader.Page_mc.startPage();",
            "this.DisableTabs(false);",
        )

    def test_transition_sound_bridge_is_feature_detected(self) -> None:
        body = _brace_block(
            self.bootstrap,
            "public static function playSound(soundName:String):Void",
        )
        self.assertIn("gfxPackage.io.GameDelegate.call == undefined", body)
        self.assertIn(
            'gfxPackage.io.GameDelegate.call("PlaySound", [soundName]);', body
        )

    def test_dynamic_panel_does_not_swap_the_journal_above_it(self) -> None:
        # The vanilla timeline's fadeOut ends with alpha=0, not _visible=false.
        # The newly-created fader is already above that timeline. Swapping the
        # two reverses the intended mouse target order, even though it looks OK.
        for source in (self.host, self.bootstrap):
            self.assertNotIn("swapDepths(_root.QuestJournalFader)", source)
            self.assertNotIn("swapDepths(_root.ConfigPanelFader)", source)
        function = _brace_block(self.bootstrap, "public static function raisePanel():Void")
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute the AS2 depth helper")
        body = function[function.index("{") + 1:-1]
        body = re.sub(r"(\bvar\s+\w+)\s*:\s*\w+", r"\1", body)
        program = "const raisePanel = new Function(" + json.dumps(body) + ");\n" + r"""
const assert = require('node:assert/strict');
function clip(depth) {
    return {depth, moves: 0, getDepth() {return this.depth;},
        swapDepths(other) {
            assert.equal(typeof other, 'number');
            this.depth = other;
            ++this.moves;
        }};
}
for (const [initialMcm, initialJournal] of [[0, -16383], [8, 2], [-10, 2], [1, 1]]) {
    const mcm = clip(initialMcm), journal = clip(initialJournal);
    globalThis._root = {ConfigPanelFader: mcm, QuestJournalFader: journal,
        getNextHighestDepth() {return Math.max(mcm.depth, journal.depth, 10) + 1;}};
    for (let i = 0; i < 4; i++) {
        mcm._visible = true; raisePanel();
        assert.ok(mcm.depth > journal.depth, 'MCM must remain the front layer on every open');
        assert.equal(journal.depth, initialJournal, 'never move a vanilla timeline layer');
        mcm._visible = false; // Closing restores the Journal through visibility, not a swap.
    }
    assert.equal(mcm.moves, initialMcm <= initialJournal ? 1 : 0);
}
globalThis._root = {}; raisePanel();
globalThis._root = {ConfigPanelFader: clip(0)}; raisePanel();
console.log('PASS: dynamic MCM stays above Journal across repeated open/close');
"""
        result = subprocess.run([node, "-e", program], text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
