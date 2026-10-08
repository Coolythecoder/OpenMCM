"""Passive mouse-probe lifecycle checks, not an emulation of Skyrim input."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/actionscript/MCMCompatMouseProbe.as"


def methods(source: str) -> dict[str, dict[str, str]]:
    result = {}
    pattern = r"function\s+(\w+)\(([^)]*)\)(?::\w+)?\s*\{"
    for match in re.finditer(pattern, source):
        level = 1
        for end in range(match.end(), len(source)):
            if source[end] == "{":
                level += 1
            elif source[end] == "}":
                level -= 1
                if not level:
                    break
        else:
            raise AssertionError(f"unclosed method {match[1]}")
        value = source[match.end():end]
        value = re.sub(r"(\bvar\s+\w+)\s*:\s*\w+", r"\1", value)
        value = re.sub(r"(catch\s*\(\w+)\s*:\s*\w+", r"\1", value)
        params = re.sub(r":\w+", "", match[2])
        result[match[1]] = {"params": params, "body": value}
    return result


class MouseProbeTests(unittest.TestCase):
    def test_probe_has_no_input_mutation_timers_or_external_output(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "setInterval(", "setTimeout(", "setFocus(", "fscommand(",
            "sendModEvent(", "AllowTextInput(", "trace(", "getURL(",
            "onPress =", "onRelease =", "onRollOver =",
        ):
            self.assertNotIn(forbidden, source)
        self.assertEqual(source.count('["hitTestDisable"] = true;'), 2)
        self.assertIn("_output.selectable = false;", source)
        self.assertIn("_mouse.getTopMostEntity(false)", source)

    def test_class_compiles_with_the_project_as2_compiler(self) -> None:
        compiler = ROOT / ".tools/mtasc-1.15/mtasc.exe"
        if not compiler.exists():
            self.skipTest("project MTASC tool has not been bootstrapped")
        with tempfile.TemporaryDirectory(prefix="openmcm-probe-") as temp:
            output = Path(temp) / "probe.swf"
            run = subprocess.run([
                str(compiler), "-cp", str(SOURCE.parent), "-header", "1280:720:30",
                "-version", "8", "-swf", str(output), str(SOURCE),
            ], capture_output=True, text=True, timeout=30)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertTrue(output.is_file())

    def test_actual_methods_are_passive_gated_and_removable(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 method bodies")
        source = SOURCE.read_text(encoding="utf-8")
        fields = re.findall(r"private var (\w+):", source)
        program = (
            "const methods = " + json.dumps(methods(source)) + ";\n"
            "const fields = " + json.dumps(fields) + ";\n"
        ) + r"""
const assert = require('node:assert/strict');
globalThis.TextFormat = function(font, size, color) {
    Object.assign(this, {font, size, color});
};
let added = [], removed = [], topCalls = [], overlays = [];
function panel() {
    return {
        _active: true, _visible: true, _state: 0, _xmouse: 172.3, _ymouse: 109.8,
        _parent: {_visible: true, getDepth() {return 4;}},
        getDepth() {return 90;}, getNextHighestDepth() {return 95;},
        _sideRows: {getDepth() {return 2;}}, _optionRows: {getDepth() {return 3;}},
        _modalLayer: {getDepth() {return 4;}}, _customLayer: {getDepth() {return 5;}},
        _journal: {getDepth() {return 6;}, _parent: {getDepth() {return 1;}}},
        createEmptyMovieClip(name, depth) {
            const clip = {
                name, depth, removeCalls: 0,
                createTextField(name, depth, x, y, width, height) {
                    this.report = {name, depth, x, y, width, height,
                        setNewTextFormat(format) {this.format = format;}};
                },
                removeMovieClip() {++this.removeCalls;}
            };
            overlays.push(clip);
            return clip;
        }
    };
}
function probe(p, mouse) {
    globalThis._global = {Mouse: mouse};
    const result = Object.fromEntries(fields.map(name => [name, undefined]));
    for (const [name, method] of Object.entries(methods))
        result[name] = new Function(method.params, 'with(this) {' + method.body + '}');
    result.MCMCompatMouseProbe(p);
    return result;
}
const mouse = {
    addListener(listener) {added.push(listener); return true;},
    removeListener(listener) {removed.push(listener); return true;},
    getTopMostEntity(testAll) {
        topCalls.push(testAll);
        return {toString() {return '_level0.host.side.row1';}, getDepth() {return 7;}};
    }
};
let p = panel(), instance = probe(p, mouse), overlay = overlays.at(-1);
assert.deepEqual(added, [instance]);
assert.equal(overlay._x, 370); assert.equal(overlay._y, 594);
assert.equal(overlay.depth, 95);
assert.equal(overlay.report.width, 810); assert.equal(overlay.report.height, 72);
assert.equal(overlay.hitTestDisable, true);
assert.equal(overlay.report.hitTestDisable, true);
assert.equal(overlay.report.selectable, false);
assert.equal(overlay.report.embedFonts, true);
assert.equal(overlay.report.format.size, 12);
assert.equal(overlay.report.type, 'dynamic');
instance.onMouseMove(); instance.onMouseDown(); instance.onMouseUp();
instance.note('side.release', 1);
assert.match(overlay.report.text, /move=1 down=1 up=1/);
assert.match(overlay.report.text, /row=side\.release #1/);
assert.match(overlay.report.text, /local x=172 y=110  state=0 active=true/);
assert.match(overlay.report.text, /top=_level0\.host\.side\.row1 @7/);
assert.match(overlay.report.text, /depth panel=90 parent=4 side=2 options=3 modal=4 custom=5 journal=6 journalParent=1/);
assert(topCalls.every(value => value === false));
instance.note('sideOver', 1); instance.note('sidePress', 1); instance.note('sideOut', 1);
assert.match(overlay.report.text, /sideOver=1 sidePress=1/);
const originalTarget = mouse.getTopMostEntity;
mouse.getTopMostEntity = () => ({toString() {return 'a'.repeat(200) + '.side.rowChosen';}});
instance.onMouseMove();
assert.match(overlay.report.text, /top=\.\.\.a+\.side\.rowChosen @\?/);
mouse.getTopMostEntity = originalTarget;
for (const gate of ['active', 'visible', 'parent']) {
    if (gate === 'active') p._active = false;
    if (gate === 'visible') p._visible = false;
    if (gate === 'parent') p._parent._visible = false;
    const previous = overlay.report.text, reads = topCalls.length;
    instance.onMouseMove(); instance.onMouseDown(); instance.onMouseUp();
    instance.note('must-not-observe', 99);
    assert.equal(overlay.report.text, previous);
    assert.equal(topCalls.length, reads);
    assert.equal(overlay._visible, false);
    p._active = true; p._visible = true; p._parent._visible = true;
}
instance.stop(); instance.stop();
assert.deepEqual(removed, [instance]);
assert.equal(overlay.removeCalls, 1);
const finalReads = topCalls.length;
instance.onMouseMove(); instance.onMouseDown(); instance.onMouseUp(); instance.note('late', 3);
assert.equal(topCalls.length, finalReads);
assert.equal(instance._panel, undefined);

// Missing or failing diagnostic-only API must not affect the host.
instance = probe(panel(), undefined);
assert.match(overlays.at(-1).report.text, /unavailable \(no Scaleform hit-test API\)/);
instance.stop();
instance = probe(panel(), {addListener() {throw Error('must not register without removal');}});
assert.equal(instance._listening, false); instance.stop();
instance = probe(panel(), {
    addListener() {throw Error('unavailable');}, removeListener() {},
    getTopMostEntity() {throw Error('unavailable');}
});
assert.equal(instance._listening, false);
assert.match(overlays.at(-1).report.text, /unavailable \(hit-test error\)/);
instance.stop();
instance = probe(undefined, mouse);
instance.onMouseMove(); instance.stop();
"""
        run = subprocess.run([node, "-e", program], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
