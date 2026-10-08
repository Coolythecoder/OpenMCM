"""Execute the independent AS2 list component with small MovieClip mocks.

These tests cover data/event ownership and stable renderer lifetime. Native
Scaleform hit testing itself is covered separately by the AVM1 fixture and
still needs an in-game check; the mock supplies hitTest results explicitly.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from test_text_input_ownership import body


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/actionscript/MCMCompatList.as"


class ListComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_text(encoding="utf-8")

    def test_native_handlers_only_created_with_pooled_renderer(self) -> None:
        render = body(self.source, "getRenderer")
        self.assertIn('if (row == undefined)', render)
        self.assertEqual(render.count('row.onPress ='), 1)
        self.assertNotIn('removeMovieClip', self.source)
        self.assertNotIn('Mouse.addListener', self.source)
        self.assertNotIn('Key.addListener', self.source)
        self.assertNotIn('hitArea =', self.source)

    def test_panel_uses_distinct_pooled_text_depths_and_current_data_aliases(self) -> None:
        source = (ROOT / "src/actionscript/MCMCompatPanel.as").read_text(encoding="utf-8")
        options = body(source, "_renderOptions")
        self.assertIn('makeText(row, "header", 3,', options)
        self.assertIn('makeText(row, "label", 1,', options)
        self.assertIn('makeText(row, "value", 2,', options)
        self.assertLess(options.index('row._alpha = disabled ? 50 : 100'),
                        options.index('if (entry.optionType == OPTION_HEADER)'))
        refresh = body(source, "setModNames")
        self.assertLess(refresh.index('_modList.entryList = _modNames'),
                        refresh.index('if (_sideMode == "pages")'))
        start = body(source, "startPage")
        self.assertIn('_pageList.entryList = _pageNames', start)
        self.assertIn('_pageList.selectIndex(-1, false)', start)
        self.assertIn('_pageList.scrollPosition = 0', start)
        custom = body(source, "loadCustomContent")
        self.assertLess(custom.index('_customContent ='), custom.index('_syncListInput()'))
        self.assertIn('list.pressIndex(undefined, 1)', body(source, "_activateCurrent"))
        cue = body(source, "_drawSideScrollCue")
        self.assertIn('if (hit == undefined)', cue)
        self.assertNotIn('cue.hitArea =', cue)

    def test_actual_panel_aliases_and_hidden_list_lifecycle(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 method bodies")
        source = (ROOT / "src/actionscript/MCMCompatPanel.as").read_text(encoding="utf-8")
        methods = {}
        names = ("_installLists", "_getSideList", "_getSideItems", "_setSideItems",
                 "_getSideIndex", "_setSideIndex", "_getSideScroll", "_setSideScroll",
                 "_getOptionEntries", "_setOptionEntries", "_getOptionIndex",
                 "_setOptionIndex", "_getOptionScroll", "_setOptionScroll",
                 "_syncListInput", "_activateCurrent", "setModNames", "startPage",
                 "loadCustomContent", "_invalidateOpenMCMPage")
        for name in names:
            arguments = re.search(rf"function\s+{name}\(([^)]*)\):\w+", source).group(1)
            code = re.sub(r":(?:Number|Boolean|MovieClip|Object|String|Void|Array|MCMCompatList)\b",
                          "", body(source, name))
            methods[name] = [re.sub(r":\w+", "", arguments), code]
        fields = re.findall(r"(?:private|public) var (\w+):", source)
        program = "const methods = " + json.dumps(methods) + ";\n"
        program += "const fields = " + json.dumps(fields) + ";\n"
        program += r"""
const assert = require('node:assert/strict');
globalThis.SIDE_VISIBLE_ROWS = 18; globalThis.PAGE_VISIBLE_ROWS = 17;
globalThis.OPTION_VISIBLE_ROWS = 12;
globalThis.READY = 0; globalThis.FOCUS_SIDE = 0; globalThis.FOCUS_OPTIONS = 1;
globalThis.OPTIONS_PANEL_X = 345; globalThis.OPTIONS_PANEL_Y = 100;
globalThis.MCMCompatUtil = {safeString: x => String(x ?? ''), translate: x => x};
globalThis.MCMCompatList = {install(clip, owner, kind) {
    return Object.assign(clip, {owner, kind, selectedIndex: -1, scrollPosition: 0,
        selectIndex(index) { this.selectedIndex = index; },
        pressIndex(index, source) { this.lastPress = {index, source}; }});
}};
function newPanel() {
    const p = Object.fromEntries(fields.map(name => [name, undefined]));
    Object.assign(p, {_parent: {_visible: true}, _visible: true,
        _sideMode: 'mods', _modNames: [{modIndex: 3, text: 'Before'}],
        _pageNames: [{pageIndex: 1, text: 'Styles'}], _optionEntries: [{id: 'option'}],
        _active: true, _focus: FOCUS_SIDE, _contentDimmed: false, _remapMode: false,
        _customContentX: 0, _customContentY: 0,
        _chrome: {createEmptyMovieClip(name) { return {_name: name, _visible: true}; }},
        _customLayer: {createEmptyMovieClip(name) {
            return {_name: name, loadMovie(source) { this.source = source; }};
        }},
        addProperty(name, get, set) {
            Object.defineProperty(this, name, {get, set: set || undefined, configurable: true});
        }
    });
    for (const name of ['_onListSelectionChange', '_onListPress', '_onListRowEvent',
            '_handleComponentInput', 'showWelcomeScreen', '_renderSide', '_renderOptions',
            '_updateFooter', '_stopModListRequest', '_beginModListRequest',
            '_focusActiveList', 'setMouseDiagnostics']) p[name] = () => {};
    for (const [name, [args, code]] of Object.entries(methods))
        p[name] = new Function(args, 'with(this) {' + code + '}');
    p.unloadCustomContent = function() { this._customContent = undefined; this._syncListInput(); };
    p._installLists();
    return p;
}
let p = newPanel();
assert.equal(p._modList.entryList, p._modNames);
assert.equal(p._pageList.entryList, p._pageNames);
assert.equal(p._optionsList.entryList, p._optionEntries);
const originalOptions = p._optionEntries;
p._sideIndex = 4; p._sideScroll = 3;
p._sideMode = 'pages'; p._sideIndex = 1; p._sideScroll = 2;
assert.equal(p._modList.selectedIndex, 4);
assert.equal(p._modList.scrollPosition, 3);
assert.equal(p._pageList.selectedIndex, 1);
assert.equal(p._pageList.scrollPosition, 2);
p._optionEntries = [{id: 'new'}]; p._optionIndex = 0; p._optionScrollRow = 5;
assert.notEqual(p._optionsList.entryList, originalOptions);
assert.equal(p._optionsList.entryList, p._optionEntries);
assert.equal(p._optionsList.selectedIndex, 0);
assert.equal(p._optionsList.scrollPosition, 10);
p._syncListInput();
assert.equal(p._modList._visible, false);
assert.equal(p._modList.disableInput, true);
assert.equal(p._pageList._visible, true);
assert.equal(p._pageList.disableInput, false);
const pages = p._pageNames, options = p._optionEntries;
p.setModNames('Zebra', 'Alpha');
assert.deepEqual(p._modList.entryList.map(x => [x.modIndex, x.text]), [[1, 'Alpha'], [0, 'Zebra']]);
assert.equal(p._pageNames, pages);
assert.equal(p._optionEntries, options);
assert.equal(p._sideMode, 'pages');
p._activateCurrent();
assert.deepEqual(p._pageList.lastPress, {index: undefined, source: 1});
assert.equal(p._modList.lastPress, undefined);
p._focus = FOCUS_OPTIONS; p._activateCurrent();
assert.deepEqual(p._optionsList.lastPress, {index: undefined, source: 1});
p.loadCustomContent('example.swf');
assert.equal(p._customContent.source, 'example.swf');
assert.equal(p._optionsList.disableInput, true);
assert.equal(p._optionsList.disableSelection, true);
p._openMCMPageReady = true; p._openMCMPageToken = 17;
p.startPage();
assert.equal(p._openMCMPageReady, false);
assert.equal(p._openMCMPageToken, 0);
assert.equal(p._sideMode, 'mods');
assert.equal(p._pageList.entryList, p._pageNames);
assert.equal(p._pageList.entryList.length, 0);
assert.equal(p._pageList.selectedIndex, -1);
assert.equal(p._pageList.scrollPosition, 0);
assert.equal(p._modList.selectedIndex, 0);
assert.equal(p._modList.disableInput, false);
assert.equal(p._pageList.disableInput, true);
"""
        run = subprocess.run([node, "-e", program], capture_output=True,
                             text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_actual_component_lifetime_and_input_contract(self) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 method bodies")
        methods = {}
        for name, arguments in re.findall(
                r"function\s+(\w+)\(([^)]*)\):\w+", self.source):
            if name == "install":
                continue
            arguments = re.sub(r":\w+", "", arguments)
            code = body(self.source, name)
            # Only AS2 annotations differ in these method bodies, including
            # the permanent native row callbacks created by getRenderer.
            code = re.sub(r":(?:Number|Boolean|MovieClip|Object|String|Void|Array)\b", "", code)
            methods[name] = [arguments, code]
        fields = re.findall(r"(?:private|public) var (\w+):", self.source)
        program = "const methods = " + json.dumps(methods) + ";\n"
        program += "const fields = " + json.dumps(fields) + ";\n"
        program += r"""
const assert = require('node:assert/strict');
globalThis._root = {_visible: true, _xmouse: 20, _ymouse: 20};
function newList(kind = 'mods') {
    const panel = {events: [], rows: [], inputs: []};
    const p = Object.fromEntries(fields.map(name => [name, undefined]));
    Object.assign(p, {
        _visible: true, _parent: _root, created: 0,
        addProperty(name, get, set) {
            Object.defineProperty(this, name, {get, set, configurable: true});
        },
        createEmptyMovieClip(name, depth) {
            ++this.created;
            return this[name] = {_name: name, _parent: this, _visible: true,
                underMouse: false, hitTest() { return this.underMouse; }};
        }
    });
    for (const [name, [args, code]] of Object.entries(methods))
        p[name] = new Function(args, 'with(this) {' + code + '}');
    p._initialize(panel, kind);
    p.onSelectionChange = function(event) { this.events.push(event); };
    p.onItemPress = function(event) { this.events.push(event); };
    p.onRowEvent = function(event) { this.rows.push(event); };
    p.onInput = function(details, path, list) {
        this.inputs.push({details, path, list}); return true;
    };
    return p;
}
function render(p, indices) {
    p.beginUpdate();
    const rows = indices.map((index, slot) => p.getRenderer(slot, index));
    p.endUpdate();
    return rows;
}
function names(p) { return p.owner.events.map(e => [e.type, e.index]); }

// Row targets, their native callbacks, and child graphics survive a repaint.
let p = newList();
p.entryList = [{name: 'A'}, {name: 'B'}, {name: 'C'}];
let rows = render(p, [0, 1]);
const row = rows[0], press = row.onPress, over = row.onRollOver;
row.label = {text: 'A'};
render(p, [1, 2]);
assert.equal(p.created, 2);
assert.equal(p.row0, row);
assert.equal(p.row0.onPress, press);
assert.equal(p.row0.onRollOver, over);
assert.equal(p.row0.label.text, 'A');
assert.equal(p.row0.itemIndex, 1);
assert.equal(p.row0.entry, p.entryList[1]);
render(p, [2]);
assert.equal(p.row1._visible, false);
assert.equal(p.row1.itemIndex, undefined);
assert.equal(p.getRendererForIndex(1), undefined);
assert.equal(p.getRendererForIndex(2), row);

// SkyUI press consumes the selection established by native rollover; it does
// not invent a selection when no row has ever been hovered or focused.
p = newList(); p.entryList = [{modIndex: 5}, {modIndex: 91}];
rows = render(p, [0, 1]);
rows[1].onPress();
assert.equal(p.selectedIndex, -1);
assert.equal(p.owner.events.length, 0);
rows[1].onRollOver();
rows[1].onPress();
assert.equal(p.selectedIndex, 1);
assert.deepEqual(names(p), [['selectionChange', 1], ['itemPress', 1]]);
assert.equal(p.owner.events[1].entry, p.entryList[1]);
assert.equal(p.owner.events[1].entry.modIndex, 91);
assert.equal(p.owner.events[1].clip, rows[1]);
assert.equal(p.owner.events[1].list, p);
assert.equal(p.owner.events[1].kind, 'mods');
assert.equal(p.owner.events[1].keyboardOrMouse, 0);
assert.deepEqual(p.owner.rows.map(e => e.type), ['rollOver', 'press']);
// The list's selected entry, not mutable panel focus or the argument passed
// into BasicList.onItemPress, is the event payload used for activation.
p.owner.events.length = 0;
rows[0].onPress();
assert.equal(p.owner.events[0].entry, p.entryList[1]);

// Every actual row path obeys list gates and hidden ancestor lifetime.
for (const gate of ['disableInput', 'disableSelection', 'isListAnimating']) {
    p = newList(); p.entryList = [{name: 'A'}]; rows = render(p, [0]);
    p.selectedIndex = 0; p[gate] = true;
    rows[0].onRollOver(); rows[0].onRollOut(); rows[0].onPress();
    p.refreshMouseSelection();
    assert.equal(p.selectedIndex, 0);
    assert.equal(p.owner.events.length, 0);
}
p = newList(); p.entryList = [{name: 'A'}]; rows = render(p, [0]);
p._parent = {_visible: false, _parent: _root};
rows[0].onRollOver(); rows[0].onPress();
assert.equal(p.owner.events.length, 0);
assert.equal(p.handleInput({}, []), false);
p._parent._visible = true;
rows[0].isEnabled = false;
rows[0].onRollOver(); rows[0].onPress();
assert.equal(p.owner.events.length, 0);
p.canSelectDisabled = true;
rows[0].onRollOver();
assert.equal(p.selectedIndex, 0);

// When a physical slot now shows another entry, stationary mouse selection
// follows the new entry, but keyboard-driven repaint does not steal selection.
p = newList(); p.entryList = [{id: 0}, {id: 1}, {id: 2}];
rows = render(p, [0, 1]);
rows[0].underMouse = true;
rows[0].onRollOver();
render(p, [1, 2]);
assert.equal(p.selectedIndex, 1);
assert.equal(p.owner.events.at(-1).entry, p.entryList[1]);
p.isMouseDrivenNav = false;
p.selectedIndex = 2;
render(p, [0, 1]);
assert.equal(p.selectedIndex, 2);

// Late rollout from another renderer does not clear the current selection.
p.isMouseDrivenNav = true; rows[1].onRollOver(); rows[0].onRollOut();
assert.equal(p.selectedIndex, 1);
rows[1].onRollOut();
assert.equal(p.selectedIndex, -1);
p.isAutoUnselect = false;
rows[1].onRollOver(); rows[1].onRollOut();
assert.equal(p.selectedIndex, 1);
p.isAutoUnselect = true;
rows[0].underMouse = false;
p.refreshMouseSelection();
assert.equal(p.selectedIndex, -1);

// Each list keeps its own selected/scroll state through sibling input.
const mods = newList('mods'), pages = newList('pages');
mods.entryList = Array.from({length: 40}, (_, i) => ({id: i}));
pages.entryList = [{page: 'General'}, {page: 'Styles'}];
mods.visibleCount = 18; mods.scrollPosition = 19; mods.selectedIndex = 23;
const pageRows = render(pages, [0, 1]);
pageRows[1].onRollOver(); pageRows[1].onPress();
assert.equal(mods.selectedIndex, 23);
assert.equal(mods.scrollPosition, 19);
assert.equal(pages.selectedIndex, 1);
mods.scrollPosition = 900;
assert.equal(mods.scrollPosition, 22);
mods.scrollPosition = -1;
assert.equal(mods.scrollPosition, 0);
const options = newList('options');
options.entryList = Array.from({length: 49}, (_, i) => ({id: i}));
options.visibleCount = 24; options.scrollDelta = 2;
options.scrollPosition = 999;
assert.equal(options.scrollPosition, 26);

// Mutation during a focus/selection callback cannot send an unrelated entry.
p = newList(); p.entryList = [{name: 'original'}]; rows = render(p, [0]);
p.onSelectionChange = function(event) { event.list.entryList = [{name: 'replacement'}]; };
rows[0].onRollOver();
rows[0].onPress();
assert.equal(p.owner.events.length, 0);
assert.equal(p.getRendererForIndex(0), undefined);

// An unclaimed renderer from the previous layout cannot be used midway
// through a new layout transaction, before endUpdate has hidden it.
p = newList(); p.entryList = [{name: 'A'}, {name: 'B'}];
rows = render(p, [0, 1]); rows[1].onRollOver();
p.owner.events.length = 0;
p.beginUpdate(); p.getRenderer(0, 0);
assert.equal(p.getRendererForIndex(1), undefined);
rows[1].onPress();
assert.equal(p.owner.events.length, 0);
p.endUpdate();

// Focus delegation goes exactly once to the supplied owner, unchanged path.
p = newList('options');
const details = {navEquivalent: 'down'}, path = [{name: 'entry'}];
assert.equal(p.handleInput(details, path), true);
assert.deepEqual(p.owner.inputs, [{details, path, list: p}]);
p.disableInput = true;
assert.equal(p.handleInput(details, path), false);
assert.equal(p.owner.inputs.length, 1);

// Invalid selections and repeated assignment are inert; silent programmatic
// changes do not emit row/selection/activation events.
p = newList(); p.entryList = [{name: 'A'}]; render(p, [0]);
for (const index of [-2, 1, 0.5, NaN]) p.selectIndex(index, true);
assert.equal(p.selectedIndex, -1);
p.selectedIndex = 0;
p.selectIndex(0, true);
assert.equal(p.owner.events.length, 0);
p.disableSelection = true;
p.selectIndex(-1, true);
assert.equal(p.selectedIndex, 0);
p.selectedIndex = -1;
assert.equal(p.selectedIndex, -1);
p.selectedIndex = 0;
p.disableSelection = false;
p.pressIndex(undefined, 1);
assert.equal(p.owner.events[0].keyboardOrMouse, 1);
"""
        run = subprocess.run([node, "-e", program], capture_output=True,
                             text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
