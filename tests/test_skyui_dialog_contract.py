from __future__ import annotations

import re
import json
import shutil
import subprocess
import unittest
from pathlib import Path

from test_text_input_ownership import body


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PANEL_PATH = REPOSITORY_ROOT / "src" / "actionscript" / "MCMCompatPanel.as"


def _between(source: str, start: str, end: str) -> str:
    start_index = source.find(start)
    end_index = source.find(end, start_index + len(start))
    if start_index < 0 or end_index < 0:
        raise AssertionError(f"missing source range {start!r} -> {end!r}")
    return source[start_index:end_index]


class SkyUIDialogContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.panel = PANEL_PATH.read_text(encoding="utf-8")

    def test_message_dialog_preserves_the_callers_wait_state(self) -> None:
        body = _between(
            self.panel,
            "public function showMessageDialog",
            "public function EndRemapMode",
        )
        self.assertIn("if (_state == READY)", body)
        self.assertIn('sendModEvent("SKICP_messageDialogClosed", null, 0)', body)
        self.assertNotIn("_state = DIALOG", body)

    def test_terminal_events_are_sent_before_dialog_teardown(self) -> None:
        accept = _between(
            self.panel,
            "private function _acceptDialog():Void",
            "private function _cancelDialog():Void",
        )
        # Local browser dialogs close in an earlier, returning branch without
        # sending provider callbacks. The legacy terminal path still publishes
        # its event before its own final teardown.
        self.assertLess(accept.rindex("sendModEvent"), accept.rindex("_closeDialog(false)"))
        self.assertLess(
            accept.index("_setTextInputEnabled(false)"),
            accept.index('sendModEvent("SKICP_inputAccepted"'),
        )

        cancel = _between(
            self.panel,
            "private function _cancelDialog():Void",
            "private function _closeDialog",
        )
        self.assertLess(cancel.rindex("sendModEvent"), cancel.rindex("_closeDialog(false)"))
        self.assertLess(cancel.index("_setTextInputEnabled(false)"), cancel.index("sendModEvent"))

    def test_slider_uses_clik_zero_based_snap_and_wheel_direction(self) -> None:
        lock = _between(
            self.panel,
            "private function _lockSliderValue",
            "private function _setSliderFromMouse",
        )
        clamp = "Math.max(minimum, Math.min(maximum, raw))"
        snap = "Math.round(value / interval) * interval"
        self.assertIn(clamp, lock)
        self.assertIn(snap, lock)
        self.assertLess(lock.index(clamp), lock.index(snap))
        self.assertNotIn("value - minimum", lock)

        wheel = _between(
            self.panel,
            "public function onMouseWheel",
            "public function onMouseMove",
        )
        self.assertIn("_adjustSlider(-delta);", wheel)

        # Representative value from CLIK Slider.lockValue.
        minimum, maximum, interval, raw = 0.05, 1.0, 0.1, 0.16
        value = max(minimum, min(maximum, raw))
        self.assertAlmostEqual(round(value / interval) * interval, 0.2)

        navigation = _between(
            self.panel,
            "private function _handleDialogNavigation",
            "private function _adjustSlider",
        )
        slider = navigation.split('if (kind == "slider") {', 1)[1].split(
            '} else if (kind == "menu") {', 1
        )[0]
        self.assertIn('nav.indexOf("left")', slider)
        self.assertIn('nav.indexOf("right")', slider)
        self.assertNotIn('nav.indexOf("down")', slider)
        self.assertNotIn('nav.indexOf("up")', slider)

    def test_color_values_round_trip_and_only_click_commits(self) -> None:
        params = _between(
            self.panel,
            "public function setColorDialogParams",
            "public function setInputDialogParams",
        )
        self.assertNotIn("& 0xFFFFFF", params)
        self.assertIn("_exactColorIndex(currentColor, palette)", params)

        render = _between(
            self.panel,
            "private function _renderColorDialog():Void",
            "private function _renderInputDialog():Void",
        )
        self.assertNotIn("swatch.onRollOver", render)
        self.assertIn("swatch.onRelease", render)
        self.assertIn("_selectColorIndex", render)

        exact = _between(
            self.panel,
            "private function _exactColorIndex",
            "private function _selectColorIndex",
        )
        self.assertIn("return -1;", exact)
        self.assertNotIn("bestDistance", exact)

        navigation = _between(
            self.panel,
            "private function _handleDialogNavigation",
            "private function _adjustSlider",
        )
        color = navigation.split('} else if (kind == "color") {', 1)[1]
        self.assertIn("if (repeated)", color)
        self.assertLess(color.index("if (repeated)"), color.index('nav.indexOf("up")'))

    def test_menu_selection_stops_at_edges_and_wheel_only_scrolls(self) -> None:
        setter = _between(
            self.panel,
            "private function _setMenuDialogSelection",
            "private function _scrollMenuDialog",
        )
        self.assertIn("Math.max(0", setter)
        self.assertIn("Math.min(_dialog.options.length - 1, index)", setter)
        self.assertNotRegex(setter, r"index\s*<\s*0.*length\s*-\s*1")

        wheel = _between(
            self.panel,
            "public function onMouseWheel",
            "public function onMouseMove",
        )
        self.assertIn("_scrollMenuDialog(delta > 0 ? -2 : 2);", wheel)
        menu_branch = wheel.split('if (_dialog.kind == "menu" &&', 1)[1].split(
            'else if (_dialog.kind == "slider" &&', 1
        )[0]
        self.assertNotIn("_setMenuDialogSelection", menu_branch)

        navigation = _between(
            self.panel,
            "private function _handleDialogNavigation",
            "private function _adjustSlider",
        )
        menu = navigation.split('} else if (kind == "menu") {', 1)[1].split(
            '} else if (kind == "color") {', 1
        )[0]
        self.assertLess(menu.index('nav.indexOf("pageup")'), menu.index('nav.indexOf("up")'))
        self.assertLess(menu.index('nav.indexOf("pagedown")'), menu.index('nav.indexOf("down")'))
        self.assertIn("_pageMenuDialog(-1);", menu)
        self.assertIn("_pageMenuDialog(1);", menu)

    def test_defaults_do_not_rebuild_text_input_and_menu_default_scrolls(self) -> None:
        navigation = _between(
            self.panel,
            "private function _handleDialogNavigation",
            "private function _adjustSlider",
        )
        self.assertIn('kind != "input" && kind != "message"', navigation)
        self.assertIn("_commitMenuDialogSelection(_dialog.defaultIndex);", navigation)

    def test_input_is_forwarded_to_the_scaleform_focus_chain(self) -> None:
        handler = _between(
            self.panel,
            "public function handleInput",
            "public function onKeyDown",
        )
        self.assertIn("var focusPath:Array = pathToFocus.slice();", handler)
        self.assertIn("focusTarget.handleInput(details, focusPath)", handler)

    def test_remap_event_precedes_prompt_teardown(self) -> None:
        body = _between(
            self.panel,
            "public function EndRemapMode",
            "public function handleInput",
        )
        self.assertLess(body.index('sendModEvent("SKICP_keymapChanged"'), body.index("_hideRemapPrompt();"))

    def test_dialog_modality_uses_component_gates_and_saved_focus(self) -> None:
        self.assertNotIn("_addModalInputBlocker", self.panel)
        self.assertNotIn('"inputBlocker"', self.panel)
        render = body(self.panel, "_renderDialog")
        self.assertLess(render.index("_modalLayer.removeMovieClip();"),
                        render.index("_acquireDialogFocus();"))
        self.assertEqual(render.count("_acquireDialogFocus();"), 1)
        self.assertIn("if (_renderedDialog != _dialog)", render)
        self.assertIn("_setContentDimmed(true);", render)
        self.assertIn("_syncListInput();", body(self.panel, "_setContentDimmed"))
        close = body(self.panel, "_closeDialog")
        self.assertLess(close.index("_setContentDimmed(false);"),
                        close.index("_restoreDialogFocus();"))

    def test_actual_dialog_focus_survives_redraws_and_list_gates_restore(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 dialog ownership")
        names = ("_acquireDialogFocus", "_restoreDialogFocus", "_syncListInput")
        methods = {
            name: re.sub(r":(?:Object|Array|Void|Boolean|Number|MovieClip)\b", "",
                         body(self.panel, name))
            for name in names
        }
        program = "const methods = " + json.dumps(methods) + ";\n" + r"""
const assert = require('node:assert/strict');
let focused, focusCalls;
globalThis._global = {gfx: {managers: {FocusHandler: {instance: {
    getFocus(controller) {assert.equal(controller, 0); return focused;}
}}}}};
function panel() {
    const p = {
        FOCUS_OPTIONS: 1, _focus: 0, _active: true,
        _contentDimmed: false, _remapMode: false, _customContent: undefined,
        _sideMode: 'mods', _modList: {}, _pageList: {}, _optionsList: {},
        _dialogFocusOwned: false, _previousDialogFocus: undefined, _modalLayer: {},
        _getSideList() {return this._sideMode === 'pages' ? this._pageList : this._modList;},
        _focusComponent(target) {focusCalls.push(target); focused = target;},
        _focusActiveList() {this._focusComponent(this._focus === 1 ? this._optionsList : this._getSideList());},
        _dispatchFocusedInput(details, path) {return details === 'key' && path.length === 0;}
    };
    for (const name of Object.keys(methods))
        p[name] = new Function('with(this) {' + methods[name] + '}');
    return p;
}
// Modal repaint replaces clips but must never replace the originating focus.
for (const mode of ['mods', 'pages', 'options', 'custom']) {
    const p = panel(); focusCalls = [];
    p._sideMode = mode === 'pages' ? 'pages' : 'mods';
    p._focus = mode === 'options' ? 1 : 0;
    const original = mode === 'custom' ? {_visible: true} :
        mode === 'options' ? p._optionsList : p._getSideList();
    focused = original;
    for (let redraw = 0; redraw < 3; ++redraw) {
        p._modalLayer = {};
        p._acquireDialogFocus();
        assert.equal(p._previousDialogFocus, original);
        assert.equal(p._dialogFocusOwned, true);
        assert.equal(focused, p._modalLayer);
        assert.equal(p._modalLayer.handleInput('key', []), true);
        p._contentDimmed = true;
        p._syncListInput();
        for (const list of [p._modList, p._pageList, p._optionsList]) {
            assert.equal(list.disableInput, true);
            assert.equal(list.disableSelection, true);
        }
    }
    p._contentDimmed = false;
    p._syncListInput();
    p._restoreDialogFocus();
    assert.equal(focused, original);
    assert.equal(p._dialogFocusOwned, false);
    assert.equal(p._previousDialogFocus, undefined);
    assert.equal(p._getSideList().disableInput, false);
    assert.equal(p._optionsList.disableInput, false);
    const hidden = p._sideMode === 'mods' ? p._pageList : p._modList;
    assert.equal(hidden.disableInput, true);
    assert.equal(hidden.disableSelection, true);
}
// A removed/hidden origin falls back to the active list. Menu teardown must
// not steal focus from the next menu after marking this panel inactive.
for (const active of [true, false]) {
    const p = panel(); focusCalls = []; focused = {_visible: true};
    const original = focused;
    p._acquireDialogFocus(); original._visible = false;
    p._active = active; focusCalls = [];
    p._restoreDialogFocus();
    assert.equal(p._dialogFocusOwned, false);
    assert.equal(p._previousDialogFocus, undefined);
    assert.deepEqual(focusCalls, active ? [p._modList] : []);
}
// Remapping, inactive panels and provider custom content keep the appropriate
// list blocked independently of the dialog's own dimmed state.
for (const reason of ['inactive', 'remap', 'custom']) {
    const p = panel();
    if (reason === 'inactive') p._active = false;
    if (reason === 'remap') p._remapMode = true;
    if (reason === 'custom') p._customContent = {};
    p._syncListInput();
    assert.equal(p._optionsList.disableInput, true);
    assert.equal(p._optionsList.disableSelection, true);
    assert.equal(p._modList.disableInput, reason !== 'custom');
}
"""
        run = subprocess.run([node, "-e", program], capture_output=True,
                             text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_actual_dialog_redraw_does_not_bounce_control_focus(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 dialog rendering")
        methods = {
            name: re.sub(r":(?:Object|Array|Void|Boolean|Number|MovieClip|TextField|TextFormat)\b", "",
                         body(self.panel, name))
            for name in ("_renderDialog", "_acquireDialogFocus", "_focusComponent")
        }
        program = "const methods = " + json.dumps(methods) + ";\n" + r"""
const assert = require('node:assert/strict');
let focused, focusCalls, removed, created;
globalThis._global = {gfx: {managers: {FocusHandler: {instance: {
    getFocus(controller) {assert.equal(controller, 0); return focused;},
    setFocus(target, controller) {
        assert.equal(controller, 0); focusCalls.push(target); focused = target;
    }
}}}}};
globalThis.MCMCompatUtil = {
    makeText() {return {textHeight: 80, getNewTextFormat() {return {};},
        setNewTextFormat() {}, setTextFormat() {}, removeTextField() {}};},
    applyDropShadow() {}, applyTextFit() {}, applyText() {}, drawLine() {},
    translateNested(value) {return value;}
};
function clip() {
    ++created;
    return {clear() {}, removeMovieClip() {++removed;}};
}
for (const kind of ['menu', 'slider', 'color', 'input', 'message']) {
    const original = {}; focused = original; focusCalls = [];
    removed = 0; created = 0;
    const p = {
        DIALOG_X: 518.5, FOCUS_OPTIONS: 1, _focus: 1, _active: true,
        _dialog: {kind, title: 'title'}, _renderedDialog: null,
        _dialogFocusOwned: false, _previousDialogFocus: undefined,
        _optionsList: original, _getSideList() {return original;},
        _modalLayer: clip(), _menuDialogList: undefined,
        _chrome: {createEmptyMovieClip() {return clip();}},
        _setTextInputEnabled() {}, _setContentDimmed() {},
        _drawDialogPanel() {}, _updateFooter() {}
    };
    for (const name of Object.keys(methods))
        p[name] = new Function(name === '_focusComponent' ? 'target' : '',
            'with(this) {' + methods[name] + '}');
    // Keep the renderer/control plumbing minimal: execute the actual lifecycle
    // and manager adapter while a persistent control represents each dialog's
    // already separately tested menu list, track, swatch, or input field.
    for (const renderer of ['Menu', 'Slider', 'Color', 'Input', 'Message'])
        p['_render' + renderer + 'Dialog'] = function() {
            if (!this._modalLayer.control) this._modalLayer.control = {};
            this._focusComponent(this._modalLayer.control);
        };
    p._renderDialog();
    const modal = p._modalLayer, control = modal.control;
    assert.deepEqual(focusCalls, [modal, control]);
    assert.equal(p._previousDialogFocus, original);
    for (let redraw = 0; redraw < 4; ++redraw) p._renderDialog();
    assert.equal(p._modalLayer, modal);
    assert.equal(p._modalLayer.control, control);
    assert.equal(focused, control);
    assert.deepEqual(focusCalls, [modal, control], kind + ' redraw bounced focus');
    assert.equal(removed, 1); assert.equal(created, 2);
    assert.equal(p._previousDialogFocus, original);

    // Replacing the dialog view acquires the new modal/control once, but does
    // not replace the saved pre-dialog origin with the old dialog's control.
    p._dialog = {kind, title: 'replacement'};
    p._renderDialog();
    assert.equal(removed, 2); assert.equal(created, 3);
    assert.equal(p._previousDialogFocus, original);
    assert.deepEqual(focusCalls, [modal, control, p._modalLayer, p._modalLayer.control]);
}
"""
        run = subprocess.run([node, "-e", program], capture_output=True,
                             text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_actual_component_focus_uses_manager_state_before_native_fallback(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 focus dispatch")
        focus_body = re.sub(r"(\bvar\s+\w+)\s*:\s*\w+", r"\1",
                            body(self.panel, "_focusComponent"))
        program = "const focusBody = " + json.dumps(focus_body) + ";\n" + r"""
const assert = require('node:assert/strict');
const focus = new Function('target', 'with(this) {' + focusBody + '}');
const panel = {_active: true};
const target = {toString() {return '_root.panel.optionsList';}};
let logicalFocus = {}, managerCalls = [];
const manager = {
    getFocus(controller) {assert.equal(controller, 0); return logicalFocus;},
    setFocus(value, controller) {
        assert.equal(controller, 0); managerCalls.push(value); logicalFocus = value;
    }
};
globalThis._global = {gfx: {managers: {FocusHandler: {instance: manager}}}};
globalThis.Selection = {
    // Native focus could already point at the target while Scaleform's logical
    // focus path is stale. This branch must not use native equality to skip
    // the manager call (and its input-path/rollover-suppression bookkeeping).
    getFocus() {throw Error('Native focus queried despite available manager');},
    setFocus() {throw Error('Native focus bypassed the available manager');}
};
focus.call(panel, target);
assert.deepEqual(managerCalls, [target]);
assert.equal(logicalFocus, target);
focus.call(panel, target);
assert.deepEqual(managerCalls, [target]); // Logical same-target assignments are redundant.
panel._active = false; focus.call(panel, {});
panel._active = true; focus.call(panel, undefined);
assert.deepEqual(managerCalls, [target]);

// Standalone AVM1 without the manager may use native focus equality solely to
// avoid generating a redundant focus change; it still assigns a new target.
_global = {};
let nativeFocus = String(target), nativeCalls = [];
Selection = {
    getFocus() {return nativeFocus;},
    setFocus(value) {nativeCalls.push(value); nativeFocus = String(value);}
};
focus.call(panel, target); assert.deepEqual(nativeCalls, []);
const next = {toString() {return '_root.panel.modList';}};
focus.call(panel, next); assert.deepEqual(nativeCalls, [next]);
"""
        run = subprocess.run([node, "-e", program], capture_output=True,
                             text=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_dialogs_use_skyui_authored_stage_geometry(self) -> None:
        render = _between(
            self.panel,
            "private function _renderDialog():Void",
            "private function _renderSliderDialog():Void",
        )
        self.assertIn('"messageProbe", 500, -1000, -1000, 330, 2000', render)
        self.assertIn('_dialog.kind == "input" ? 49.673 : 46.873', render)
        self.assertIn('dialogY + 98.373 : dialogY + dialogHeight - 48.5', render)

        input_dialog = _between(
            self.panel,
            "private function _renderInputDialog():Void",
            "private function _renderMessageDialog():Void",
        )
        self.assertIn("530.887, top + 50.623", input_dialog)
        self.assertIn("376.236, 46.756, 0x141414, 89.84", input_dialog)
        self.assertIn('createTextField("inputField", 10, 537.5', input_dialog)
        self.assertIn("top + 55, 367, 42", input_dialog)

        message = _between(
            self.panel,
            "private function _renderMessageDialog():Void",
            "private function _makeButton",
        )
        self.assertIn("var contentHeight:Number = height - 78;", message)
        self.assertIn("556, top + 14, 330, contentHeight", message)
        self.assertIn("top + height - 50", message)

    def test_dialog_button_panels_are_unplated_and_right_ordered(self) -> None:
        button = _between(
            self.panel,
            "private function _makeButton",
            "private function _placeLeftButton",
        )
        self.assertNotIn("drawPolygon(button", button)
        self.assertIn('createEmptyMovieClip("hitArea", 0)', button)
        self.assertIn("0x000000, 0, 0x000000, 0", button)
        self.assertIn("_dialogControlName(action)", button)
        self.assertIn("0, 2, 150, 27.7, 20", button)
        self.assertIn('label.autoSize = "left";', button)

        input_dialog = _between(
            self.panel,
            "private function _renderInputDialog():Void",
            "private function _renderMessageDialog():Void",
        )
        self.assertIn('"inputCancel", 20', input_dialog)
        self.assertIn('"inputAccept", 21', input_dialog)
        self.assertIn("886, top + 104.85", input_dialog)

        message = _between(
            self.panel,
            "private function _renderMessageDialog():Void",
            "private function _makeButton",
        )
        self.assertIn('"messageCancel", 20', message)
        self.assertIn('"messageAccept", 21', message)
        self.assertIn('"messageAccept", 21, 885', message)

        reversed_panel = _between(
            self.panel,
            "private function _placeRightButtons",
            "private function _dialogControlName",
        )
        self.assertIn("cancelButton._x - 10", reversed_panel)

    def test_dialog_dimming_leaves_titlebar_opaque(self) -> None:
        dim = _between(
            self.panel,
            "private function _setContentDimmed",
            "private function _acquireDialogFocus",
        )
        self.assertNotIn("_titlePlate._alpha", dim)
        self.assertNotIn("_titleField._alpha", dim)
        self.assertIn("_optionRows._alpha = alpha;", dim)

    def test_partial_buffer_writes_and_cursor_persistence_match_skyui(self) -> None:
        for name in (
            "setOptionFlagsBuffer",
            "setOptionTextBuffer",
            "setOptionStrValueBuffer",
            "setOptionNumValueBuffer",
        ):
            body = _between(
                self.panel,
                f"public function {name}",
                "\n\tpublic function",
            )
            self.assertNotRegex(body, r"_option\w+Buffer\s*=\s*\[\]")

        flush = _between(
            self.panel,
            "public function flushOptionBuffers",
            "private function _getOptionCursor",
        )
        self.assertNotIn("optionCursorIndex = -1", flush)

    def test_ordinary_unlock_does_not_synthesize_highlight_events(self) -> None:
        unlock = _between(
            self.panel,
            "public function unlock",
            "public function setModNames",
        )
        self.assertIn("_selectActivePage();", unlock)
        self.assertNotIn("_initHighlight", unlock)
        self.assertNotIn("else if", unlock)


if __name__ == "__main__":
    unittest.main()
