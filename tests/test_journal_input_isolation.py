"""Journal lifecycle follows SkyUI without a blanket host-input workaround.

Run the actual fallback/patch method bodies against observable host mocks. The
dynamic MCM is depth-ordered above the authored Journal by raisePanel, whereas
SkyUI swaps two pre-authored faders. Neither path should change Journal-wide
visibility or hit-test flags. These tests do not emulate Scaleform mouse picking.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from test_journal_lifecycle import _brace_block, _here_string


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "src/actionscript/MCMCompatBootstrap.as"
PANEL = ROOT / "src/actionscript/MCMCompatPanel.as"
PATCH = ROOT / "scripts/Patch-Journal.ps1"


def _method_body(source: str, marker: str) -> str:
    method = _brace_block(source, marker)
    return re.sub(r"(\bvar\s+\w+)\s*:\s*\w+", r"\1",
                  method[method.index("{") + 1:-1])


class JournalInputIsolationTests(unittest.TestCase):
    def test_no_blanket_journal_visibility_or_hit_test_ownership(self) -> None:
        for path in (BOOTSTRAP, PANEL, PATCH):
            with self.subTest(path=path):
                source = path.read_text(encoding="utf-8")
                for rejected in ("suspendJournalInput", "restoreJournalInput",
                                 "_journalInputState"):
                    self.assertNotIn(rejected, source)
        # The host integration must not borrow Scaleform's entire-subtree input
        # flag; list components own their own disabled/selection states instead.
        self.assertNotIn("hitTestDisable", BOOTSTRAP.read_text(encoding="utf-8"))

    def test_actual_open_close_preserve_journal_flags_and_transition_order(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 method bodies")
        bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
        patched = _here_string(PATCH.read_text(encoding="utf-8"), "hostMethods")
        implementations = {}
        for name, source, open_marker, close_marker in (
            ("fallback", bootstrap, "journal.ConfigPanelOpen = function():Void",
             "journal.ConfigPanelClose = function():Void"),
            ("patched", patched, "function ConfigPanelOpen()",
             "function ConfigPanelClose()"),
        ):
            implementations[name] = {
                "open": _method_body(source, open_marker),
                "close": _method_body(source, close_marker),
            }
        program = "const implementations = " + json.dumps(implementations) + ";\n"
        program += r"""
const assert = require('node:assert/strict');
for (const [implementation, methods] of Object.entries(implementations)) {
    for (const initialVisible of [true, false]) {
        for (const initialInput of [true, false, undefined]) {
            const calls = [];
            const journalFader = {};
            // Catch assignments even when they would restore the same value.
            Object.defineProperties(journalFader, {
                _visible: {get() {return initialVisible;},
                    set() {throw Error('Journal visibility mutation');}},
                hitTestDisable: {get() {return initialInput;},
                    set() {throw Error('Journal hit-test mutation');}}
            });
            let mcmVisible = false;
            const mcmFader = {};
            Object.defineProperty(mcmFader, '_visible', {
                get() {return mcmVisible;},
                set(value) {mcmVisible = value; calls.push('mcmVisible:' + value);}
            });
            const panel = {
                startPage() {calls.push('mcmStart');},
                endPage() {calls.push('mcmEnd');}
            };
            const journal = {
                ConfigPanel: panel,
                SystemFader: {Page_mc: {
                    startPage() {calls.push('systemStart');},
                    endPage() {calls.push('systemEnd');}
                }},
                DisableTabs(value) {calls.push('tabs:' + value);},
                DoHideMenu() {calls.push('fadeOut');},
                DoShowMenu() {calls.push('fadeIn');}
            };
            globalThis._root = {ConfigPanelFader: mcmFader, QuestJournalFader: journalFader};
            globalThis.gfx = {managers: {FocusHandler: {instance: {
                setFocus(target, controller) {
                    assert.equal(controller, 0);
                    calls.push('focus:' + (target === panel ? 'mcm' : 'journal'));
                    assert(target === panel || target === journal);
                }
            }}}};
            globalThis._global = {gfx};
            globalThis.MCMCompatBootstrap = {
                raisePanel() {calls.push('raiseMcm');},
                playSound(name) {calls.push('sound:' + name);}
            };
            const open = new Function(methods.open), close = new Function(methods.close);
            for (let cycle = 0; cycle < 3; ++cycle) {
                calls.length = 0;
                open.call(journal);
                assert.deepEqual(calls, ['tabs:true', 'systemEnd', 'fadeOut',
                    'mcmVisible:true', 'raiseMcm', 'focus:mcm', 'sound:UIMenuOK',
                    'mcmStart'], implementation + ' open');
                assert.equal(mcmVisible, true);
                calls.length = 0;
                close.call(journal);
                assert.deepEqual(calls, ['sound:UIMenuCancel', 'mcmEnd', 'mcmVisible:false',
                    'focus:journal', 'fadeIn', 'systemStart', 'tabs:false'],
                    implementation + ' close');
                assert.equal(mcmVisible, false);
                assert.equal(journalFader._visible, initialVisible);
                assert.equal(journalFader.hitTestDisable, initialInput);
            }
        }
    }
}
"""
        result = subprocess.run([node, "-e", program], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fallbacks_preserve_existing_host_methods(self) -> None:
        source = BOOTSTRAP.read_text(encoding="utf-8")
        install = _brace_block(source, "private static function installJournalFallbacks")
        self.assertIn("if (journal.ConfigPanelOpen == undefined)", install)
        self.assertIn("if (journal.ConfigPanelClose == undefined)", install)
        self.assertIn("if (journal.DisableTabs == undefined)", install)


if __name__ == "__main__":
    unittest.main()
