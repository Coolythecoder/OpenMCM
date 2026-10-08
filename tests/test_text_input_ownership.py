"""Execute the small AS2 ownership/teardown methods as JavaScript with SKSE mocks.

This verifies counter ownership and callback ordering, not the Skyrim runtime,
Scaleform focus, or the cause of a whole-game freeze.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "src/actionscript/MCMCompatPanel.as"
UTIL = ROOT / "src/actionscript/MCMCompatUtil.as"


def body(source: str, name: str) -> str:
    match = re.search(rf"function\s+{re.escape(name)}\([^)]*\):\w+\s*\{{", source)
    if not match:
        raise AssertionError(f"missing function {name}")
    start = match.end()
    depth = 1
    for end in range(start, len(source)):
        if source[end] == "{":
            depth += 1
        elif source[end] == "}":
            depth -= 1
            if not depth:
                return source[start:end]
    raise AssertionError(f"unclosed function {name}")


class TextInputOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.panel = PANEL.read_text(encoding="utf-8")
        cls.util = UTIL.read_text(encoding="utf-8")

    def test_only_owned_helper_can_call_the_bridge(self) -> None:
        self.assertIn("_textInputOwned = false;", self.panel)
        self.assertEqual(self.panel.count("MCMCompatUtil.allowTextInput("), 1)
        helper = body(self.panel, "_setTextInputEnabled")
        self.assertIn("if (enabled == _textInputOwned)", helper)
        self.assertLess(helper.index("return;"), helper.index("MCMCompatUtil.allowTextInput"))
        self.assertIn("if (MCMCompatUtil.allowTextInput(enabled))", helper)
        self.assertIn("_textInputOwned = enabled;", helper)

    def test_teardown_releases_owned_input_even_without_a_dialog(self) -> None:
        close = body(self.panel, "_closeDialog")
        self.assertLess(close.index("_setTextInputEnabled(false)"), close.index("if (_dialog == null)"))
        self.assertIn("_setTextInputEnabled(false)", body(self.panel, "onUnload"))
        self.assertIn("_closeDialog(false)", body(self.panel, "endPage"))

    def test_actual_ownership_and_teardown_methods_preserve_other_menu_counter(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 method bodies")

        methods = {name: body(self.panel, name) for name in (
            "_setTextInputEnabled", "_acceptDialog", "_cancelDialog", "_closeDialog", "onUnload",
            "_invalidateOpenMCMPage"
        )}
        methods["allowTextInput"] = body(self.util, "allowTextInput")
        # AS2's typed local declarations are the only syntax difference in
        # these methods. `with(this)` gives unqualified AS2 members their
        # normal receiver scope. No replacement implementation is tested.
        methods = {name: re.sub(r"(\bvar\s+\w+)\s*:\s*\w+", r"\1", value)
                   for name, value in methods.items()}
        program = "const bodies = " + json.dumps(methods) + ";\n" + r"""
const assert = require('node:assert/strict');
let count, calls, terminal;
globalThis._global = {};
globalThis._root = {};
globalThis.Mouse = {removeListener() {}};
globalThis.Key = {removeListener() {}};
globalThis.Selection = {setFocus() {}};
const bridge = {AllowTextInput(enabled) {
    calls.push(enabled);
    if (enabled) ++count;
    else if (count > 0) --count;
}};
globalThis.MCMCompatUtil = {
    allowTextInput: new Function('enabled', bodies.allowTextInput),
    sendModEvent(...args) { terminal(...args); }
};
function panel() {
    const p = {
        _textInputOwned: false, _dialog: null, _inputField: undefined,
        _openMCMPageReady: true, _openMCMPageToken: 17,
        _sliderDragging: false, _highlightIntervalID: undefined,
        _remapDelayID: undefined, _modalLayer: {removeMovieClip() {}},
        _chrome: {createEmptyMovieClip() {return {removeMovieClip() {}};}},
        _stopModListRequest() {}, _setContentDimmed() {}, _updateFooter() {},
        _syncListInput() {}, _restoreDialogFocus() {}
    };
    for (const name of Object.keys(bodies)) {
        if (name === 'allowTextInput') continue;
        const param = name === '_setTextInputEnabled' ? 'enabled' :
            name === '_closeDialog' ? 'sendCancel' : '';
        p[name] = new Function(param, 'with(this) {' + bodies[name] + '}');
    }
    return p;
}
function reset() {
    count = 1; // Another menu owns one text-input request.
    calls = [];
    _global.skse = bridge;
    _root.skse = undefined;
    terminal = () => {};
}
reset();
let p = panel();
p._closeDialog(false);
p.onUnload(); p.onUnload();
assert.equal(p._openMCMPageReady, false);
assert.equal(p._openMCMPageToken, 0);
assert.equal(count, 1);
assert.deepEqual(calls, []); // Unused Journal must not touch global input.
for (const kind of ['slider', 'menu', 'color', 'message']) {
    p._dialog = {kind};
    p._closeDialog(false);
}
assert.equal(count, 1);
assert.deepEqual(calls, []);

for (const action of ['_acceptDialog', '_cancelDialog']) {
    reset(); p = panel();
    p._setTextInputEnabled(true);
    p._setTextInputEnabled(true);
    assert.equal(count, 2);
    p._dialog = {kind: 'input', text: 'kept'};
    // Even if the TextField was already removed, release before the callback.
    p._inputField = undefined;
    let sent = 0;
    terminal = () => {
        ++sent;
        assert.equal(count, 1);
        assert.equal(p._textInputOwned, false);
        ++count; // A callback/another menu acquires text input before cleanup.
    };
    p[action]();
    p.onUnload(); p.onUnload();
    assert.equal(sent, 1);
    assert.equal(count, 2); // Late cleanup cannot steal the new request.
    assert.deepEqual(calls, [true, false]);
}

reset(); p = panel();
_global.skse = {}; // A bridge object without the API is also unavailable.
p._setTextInputEnabled(true);
assert.equal(p._textInputOwned, false);
assert.deepEqual(calls, []);

reset(); p = panel();
p._setTextInputEnabled(true);
p._dialog = {kind: 'input', text: 'old'};
p._inputField = {text: 'new'};
terminal = (event, text) => {
    assert.equal(event, 'SKICP_inputAccepted');
    assert.equal(text, 'new');
    assert.equal(count, 1);
};
p._acceptDialog();
p.onUnload();
assert.equal(count, 1);
assert.deepEqual(calls, [true, false]);

reset(); p = panel();
_global.skse = undefined;
p._setTextInputEnabled(true);
assert.equal(p._textInputOwned, false);
assert.deepEqual(calls, []);
_root.skse = bridge; // Exercise fallback and retry after bridge availability.
p._setTextInputEnabled(true);
assert.equal(count, 2);
_root.skse = undefined;
p._setTextInputEnabled(false);
assert.equal(p._textInputOwned, true); // Failed release is not recorded as success.
_root.skse = bridge;
p.onUnload(); p.onUnload();
assert.equal(count, 1);
assert.deepEqual(calls, [true, false]);

reset(); p = panel();
const other = panel();
p._setTextInputEnabled(true);
other._setTextInputEnabled(true);
p.onUnload(); p.onUnload();
assert.equal(count, 2);
other.onUnload();
assert.equal(count, 1);
console.log('PASS: actual AS2 ownership/cleanup bodies preserve external input requests');
"""
        result = subprocess.run([node, "-e", program], text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
