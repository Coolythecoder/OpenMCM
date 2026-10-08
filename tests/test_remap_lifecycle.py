"""Execute AS2 remap ownership ordering with the actual list-gate methods."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from test_text_input_ownership import body


PANEL = Path(__file__).resolve().parents[1] / "src/actionscript/MCMCompatPanel.as"


class RemapLifecycleTests(unittest.TestCase):
    def test_failed_start_restores_list_input_before_restoring_focus(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 methods")
        source = PANEL.read_text(encoding="utf-8")
        names = ("_startRemap", "_hideRemapPrompt", "_syncListInput", "_clearRemap")
        methods = {}
        for name in names:
            match = re.search(rf"function\s+{name}\(([^)]*)\):\w+", source)
            code = re.sub(r"(\bvar\s+\w+)\s*:\s*\w+", r"\1", body(source, name))
            methods[name] = [re.sub(r":\w+", "", match.group(1)), code]
        program = "const methods = " + json.dumps(methods) + ";\n" + r"""
const assert = require('node:assert/strict');
globalThis.READY = 0;
let starts = 0, available = false;
globalThis.MCMCompatUtil = {startRemapMode(panel) {
    ++starts;
    assert.equal(panel._remapMode, true);
    assert.equal(panel._pageList.disableInput, true);
    assert.equal(panel._optionsList.disableInput, true);
    return available;
}};
function clip() { return {removeMovieClip() {this.removed = true;}}; }
function panel() {
    const p = {
        _active: true, _sideMode: 'pages', _remapMode: false,
        _contentDimmed: false, _customContent: undefined,
        _state: READY, _currentRemapOption: -1, _remapDelayID: undefined,
        _modList: {}, _pageList: {}, _optionsList: {},
        _modalLayer: clip(), _chrome: {createEmptyMovieClip: clip},
        _setContentDimmed(value) {this._contentDimmed = value; this._syncListInput();},
        _showRemapPrompt() {this._setContentDimmed(true);},
        _restoreDialogFocus() {
            ++this.restores;
            assert.equal(this._remapMode, false);
            assert.equal(this._pageList.disableInput, false);
            assert.equal(this._pageList.disableSelection, false);
            assert.equal(this._optionsList.disableInput, false);
            assert.equal(this._optionsList.disableSelection, false);
        },
        _focusActiveList() { ++this.focuses; }, restores: 0, focuses: 0
    };
    for (const [name, [args, code]] of Object.entries(methods))
        p[name] = new Function(args, 'with(this) {' + code + '}');
    p._syncListInput();
    return p;
}
let p = panel();
const prompt = p._modalLayer;
p._startRemap(12);
assert.equal(starts, 1);
assert.equal(p._currentRemapOption, -1);
assert.equal(p._remapMode, false);
assert.equal(p._state, READY);
assert.equal(p._contentDimmed, false);
assert.equal(prompt.removed, true);
assert.equal(p.restores, 1);
assert.equal(p._modList.disableInput, true); // Hidden sibling remains gated.

// A failed bridge start may be retried after the API becomes available.
available = true;
p._startRemap(14);
assert.equal(starts, 2);
assert.equal(p._currentRemapOption, 14);
assert.equal(p._remapMode, true);
assert.equal(p._pageList.disableInput, true);
assert.equal(p._optionsList.disableInput, true);
assert.equal(p.restores, 1);
p._startRemap(15); // No duplicate native capture while ownership is held.
assert.equal(starts, 2);
assert.equal(p._currentRemapOption, 14);

// The normal delayed completion still clears remap ownership and re-enables
// the component gates after the prompt has been dismissed.
p._contentDimmed = false;
p._clearRemap();
assert.equal(p._remapMode, false);
assert.equal(p._currentRemapOption, -1);
assert.equal(p._pageList.disableInput, false);
assert.equal(p._optionsList.disableInput, false);
assert.equal(p._modList.disableInput, true);
assert.equal(p.focuses, 1);
"""
        run = subprocess.run([node, "-e", program], capture_output=True,
                             text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
