"""Regression checks for SkyUI-style HTML in MCM option text.

The Node fixture executes the actual AS2 helper bodies with a small TextField
run-format model. It checks API ordering and format preservation, not Flash's
HTML parser, font availability, layout, or an in-game rendering result. The
normal build separately compiles the complete ActionScript into the real SWF.

SkyUI's ModConfigPanel/OptionsListEntry.as uses SetText(..., true) for option
headers, labels, and values. Other MCM text surfaces remain plain text.
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


MODEL = r"""
const assert = require('node:assert/strict');
const copy = value => Object.assign({}, value);
globalThis.TextFormat = function TextFormat() {};
const baseline = {
    font: '$EverywhereFont', size: 22, color: 0xFFFFFF, bold: false,
    italic: false, underline: false, align: 'left', leading: 2,
    letterSpacing: 0.8, kerning: true
};

// This intentionally models only the semantics the helper must respect:
// HTML produces separately formatted runs, setTextFormat overwrites supplied
// properties on every run, and get/setNewTextFormat owns the future default.
// The tiny parser below is test fixture code, not a replacement Flash parser.
class Field {
    constructor(format = baseline) {
        this.next = copy(format);
        this.runs = [];
        this.html = false;
        this.calls = [];
    }
    getNewTextFormat() { this.calls.push(['getNew']); return copy(this.next); }
    setNewTextFormat(format) {
        this.calls.push(['setNew', copy(format)]);
        this.next = copy(format);
    }
    getTextFormat() {
        this.calls.push(['getCurrent']);
        const result = copy(this.runs.length ? this.runs[0].format : this.next);
        for (const run of this.runs) {
            for (const key of Object.keys(result)) {
                if (run.format[key] !== result[key]) result[key] = null;
            }
        }
        return result;
    }
    setTextFormat(format) {
        this.calls.push(['set', copy(format)]);
        // AVM1 aggregate formats use null for attributes that vary by run.
        // Reapplying those null attributes must not flatten the mixed runs.
        for (const run of this.runs) {
            for (const [key, value] of Object.entries(format)) {
                if (value != null) run.format[key] = value;
            }
        }
    }
    set text(value) {
        this.calls.push(['text', value]);
        this.runs = value === '' ? [] : [{text: value, format: copy(this.next)}];
    }
    get text() { return this.runs.map(run => run.text).join(''); }
    set htmlText(value) {
        this.calls.push(['htmlText', value]);
        assert.equal(this.html, true, 'HTML mode must be enabled before assignment');
        this.runs = [];
        const formats = [copy(this.htmlDefaults || this.next)];
        for (const token of value.match(/<[^>]*>|[^<]+/g) || []) {
            if (/^<\/(font|b|i|u|p|textformat)>$/i.test(token)) {
                if (formats.length > 1) formats.pop();
            } else if (/^<(font|b|i|u|p|textformat)\b/i.test(token)) {
                const next = copy(formats[formats.length - 1]);
                for (const attr of token.matchAll(/(color|face|size|align|leading)\s*=\s*["']([^"']*)["']/gi)) {
                    const key = attr[1].toLowerCase();
                    if (key === 'color') next.color = parseInt(attr[2].replace('#', ''), 16);
                    if (key === 'face') next.font = attr[2];
                    if (key === 'size') next.size = Number(attr[2]);
                    if (key === 'align') next.align = attr[2];
                    if (key === 'leading') next.leading = Number(attr[2]);
                }
                if (/^<b>/i.test(token)) next.bold = true;
                if (/^<i>/i.test(token)) next.italic = true;
                if (/^<u>/i.test(token)) next.underline = true;
                formats.push(next);
            } else if (token[0] !== '<') {
                this.runs.push({text: token, format: copy(formats[formats.length - 1])});
            }
        }
        // Exercise a renderer that updates its insertion format while parsing.
        // Restoring the saved default must work regardless of that behavior.
        if (this.runs.length) this.next = copy(this.runs[0].format);
    }
}
globalThis.MCMCompatUtil = {};
for (const name of ['safeString', 'hexColor', 'escapeHtmlAttribute', 'applyText', 'applyHtmlText']) {
    const params = ['safeString', 'hexColor', 'escapeHtmlAttribute'].includes(name) ? ['value'] : ['field', 'value'];
    MCMCompatUtil[name] = new Function(...params,
        'with(MCMCompatUtil) {' + bodies[name] + '}');
}
// Translation and number formatting are outside these formatting tests. They
// remain explicit dependency stubs; _formatOptionValue itself is real source.
MCMCompatUtil.translateNested = value => MCMCompatUtil.safeString(value);
MCMCompatUtil.translate = value => MCMCompatUtil.safeString(value);
MCMCompatUtil.formatSlider = (format, value) => format.replace('{1}', value.toFixed(1));
MCMCompatUtil.keyName = value => 'Key ' + value;
const panel = {OPTION_TEXT: 2, OPTION_TOGGLE: 3, OPTION_SLIDER: 4,
    OPTION_MENU: 5, OPTION_KEYMAP: 7, OPTION_INPUT: 8};
panel._formatOptionValue = new Function('entry',
    'with(this) {' + bodies._formatOptionValue + '}');
const html = (field, value) => MCMCompatUtil.applyHtmlText(field, value);
const plain = (field, value) => MCMCompatUtil.applyText(field, value);
"""


class FormattedTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.panel = PANEL.read_text(encoding="utf-8")
        cls.util = UTIL.read_text(encoding="utf-8")

    def run_model(self, assertions: str) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 text method bodies")
        methods = {name: body(self.util, name) for name in
                   ("safeString", "hexColor", "escapeHtmlAttribute", "applyText", "applyHtmlText")}
        methods["_formatOptionValue"] = body(self.panel, "_formatOptionValue")
        # Typed local declarations are the only AS2-only syntax in these bodies.
        methods = {name: re.sub(r"(\bvar\s+\w+)\s*:\s*\w+", r"\1", value)
                   for name, value in methods.items()}
        program = "const bodies = " + json.dumps(methods) + ";\n" + MODEL + assertions
        result = subprocess.run([node, "-e", program], text=True,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_only_option_header_label_and_value_enable_html(self) -> None:
        render = body(self.panel, "_renderOptions")
        self.assertEqual(self.panel.count("MCMCompatUtil.applyHtmlText("), 3)
        self.assertEqual(render.count("MCMCompatUtil.applyHtmlText("), 3)
        self.assertRegex(render, r"applyHtmlText\(header,\s*(?:String\()?entry\.text")
        self.assertIn("MCMCompatUtil.applyHtmlText(label, entry.text)", render)
        self.assertIn("MCMCompatUtil.applyHtmlText(value, _formatOptionValue(entry))", render)
        self.assertNotRegex(self.panel, r"\.html(?:Text)?\s*=")
        self.assertEqual(len(re.findall(r"\.htmlText\s*=", self.util)), 1)
        self.assertNotRegex(render, r"entry\.(?:text|strValue)\s*=")

    def test_non_option_text_stays_plain(self) -> None:
        for statement in (
            "MCMCompatUtil.applyText(_titleField, _titleText)",
            "MCMCompatUtil.applyText(_infoField, MCMCompatUtil.unescapeText(_infoText))",
            "MCMCompatUtil.applyText(label, _sideItems[i].text)",
            "MCMCompatUtil.applyText(label, options[i])",
            "MCMCompatUtil.applyText(message, _dialog.text)",
        ):
            self.assertIn(statement, self.panel)
        self.assertRegex(self.panel, r'_inputField\.text\s*=')
        self.assertIn("field.html = false;", body(self.util, "applyText"))

    def test_mixed_color_spans_survive_without_full_format_overwrite(self) -> None:
        self.run_model(r"""
const field = new Field();
html(field, '<font color="#FF2200">Red</font> plain <font color="#11BB33">Green</font>');
assert.equal(field.text, 'Red plain Green');
assert.deepEqual(field.runs.map(run => run.format.color), [0xFF2200, 0xFFFFFF, 0x11BB33]);
assert.deepEqual(field.next, baseline);
const writes = field.calls.filter(call => call[0] === 'set');
assert.equal(writes.length, 1);
assert.equal(writes[0][1].color, null, 'mixed colors stay unset in aggregate format');
assert.equal(writes[0][1].font, baseline.font);
assert.equal(writes[0][1].letterSpacing, 0.8);
assert.equal(writes[0][1].kerning, true);
assert.equal(field.calls[0][0], 'getNew');
assert.ok(field.calls.findIndex(call => call[0] === 'getCurrent') >
    field.calls.findIndex(call => call[0] === 'htmlText'));
assert.ok(field.calls.findIndex(call => call[0] === 'setNew') >
    field.calls.findIndex(call => call[0] === 'htmlText'));
""")

    def test_html_spacing_uses_parsed_format_not_constructor_defaults(self) -> None:
        self.run_model(r"""
// Deliberately model a default-bearing constructor, not just the old empty
// object mock. The helper must preserve parsed runs in either environment.
globalThis.TextFormat = function TextFormat() {
    Object.assign(this, {font: 'Times New Roman', size: 12, color: 0,
        bold: false, italic: false, underline: false, align: 'left'});
};
for (const format of [baseline,
    {...baseline, font: '$EverywhereMediumFont', kerning: true},
    {...baseline, font: '$EverywhereBoldFont', size: 20, bold: true, align: 'right'}]) {
    const field = new Field(format);
    html(field, 'Begin Your Adventure');
    assert.deepEqual(field.runs[0].format, format);
    html(field, '<font color="#FF2200">Red</font> white <font color="#11BB33">Green</font>');
    assert.deepEqual(field.runs.map(run => run.format.color), [0xFF2200, 0xFFFFFF, 0x11BB33]);
    assert.ok(field.runs.every(run => run.format.font === format.font && run.format.size === format.size));
    assert.deepEqual(field.next, format);
}
""")

    def test_skyui_html_format_readback_order_is_retained(self) -> None:
        method = body(self.util, "applyHtmlText")
        self.assertNotIn("new TextFormat", method)
        self.assertLess(method.index("field.htmlText ="), method.index("field.getTextFormat()"))
        self.assertLess(method.index("field.getTextFormat()"), method.index("field.setTextFormat("))
        self.assertLess(method.index("field.setTextFormat("), method.index("field.setNewTextFormat(baseline)"))

    def test_plain_options_use_explicit_game_format_without_html_parsing(self) -> None:
        self.run_model(r"""
const field = new Field();
html(field, 'Begin Your Adventure');
assert.equal(field.html, false);
assert.ok(!field.calls.some(call => call[0] === 'htmlText'));
assert.deepEqual(field.runs[0].format, baseline);
""")

    def test_html_defaults_are_explicit_when_document_defaults_differ(self) -> None:
        self.run_model(r"""
for (const format of [baseline,
    {...baseline, font:'$EverywhereMediumFont', leading:0},
    {...baseline, font:'$EverywhereBoldFont', size:20, bold:true, align:'right'}]) {
    const field = new Field(format);
    // Model dynamic HTML starting with document defaults instead of the
    // field's insertion format. The native emulator does not model Skyrim.
    field.htmlDefaults = {...format, font:'Times New Roman', size:12, color:0,
        bold:false, italic:false, underline:false, align:'left', leading:0};
    html(field, 'White <font color="#E86BA5">Pink</font> White');
    assert.deepEqual(field.runs.map(run => run.format.color), [0xFFFFFF,0xE86BA5,0xFFFFFF]);
    for (const run of field.runs) {
        for (const key of ['font','size','bold','align','leading','letterSpacing','kerning'])
            assert.equal(run.format[key],format[key],key);
    }
    assert.deepEqual(field.next,format);
}
""")

    def test_translation_happens_before_plain_or_html_dispatch(self) -> None:
        self.run_model(r"""
MCMCompatUtil.translate = value => value === '$LABEL' ? '<font color="#E86BA5">Translated</font>' : 'Plain label';
const field = new Field();
html(field, '$LABEL');
assert.equal(field.text,'Translated');
assert.equal(field.runs[0].format.color,0xE86BA5);
html(field, '$PLAIN');
assert.equal(field.text,'Plain label');
assert.equal(field.html,false);
assert.deepEqual(field.runs[0].format,baseline);
""")

    def test_attribute_escaping_does_not_escape_the_mcm_payload(self) -> None:
        self.run_model(r"""
assert.equal(MCMCompatUtil.escapeHtmlAttribute('A&"<B>'),'A&amp;&quot;&lt;B&gt;');
const field = new Field();
const payload = '<font color="#E86BA5">Pink</font>';
html(field,payload);
const assigned = field.calls.find(call => call[0] === 'htmlText')[1];
assert.ok(assigned.includes(payload));
assert.ok(!assigned.includes('&lt;font color'));
""")

    def test_font_size_and_inline_styles_survive_spacing_reapplication(self) -> None:
        self.run_model(r"""
const field = new Field();
html(field, '<font face="$EverywhereMediumFont" size="28" color="#123456"><b><i><u>Styled</u></i></b></font> normal');
const style = field.runs[0].format;
assert.equal(style.font, '$EverywhereMediumFont');
assert.equal(style.size, 28);
assert.equal(style.color, 0x123456);
assert.equal(style.bold, true);
assert.equal(style.italic, true);
assert.equal(style.underline, true);
assert.equal(style.letterSpacing, baseline.letterSpacing);
assert.equal(style.kerning, baseline.kerning);
assert.deepEqual(field.runs[1].format, baseline);
assert.deepEqual(field.next, baseline);
""")

    def test_reused_field_does_not_bleed_html_color_into_next_content(self) -> None:
        self.run_model(r"""
const field = new Field();
html(field, '<font color="#0088FF" size="30">First</font>');
html(field, 'Second');
assert.equal(field.text, 'Second');
assert.deepEqual(field.runs[0].format, baseline);
html(field, '<font color="#FF0000">Third</font>');
plain(field, 'Fourth');
assert.equal(field.html, false);
assert.equal(field.text, 'Fourth');
assert.deepEqual(field.runs[0].format, baseline);
assert.deepEqual(field.next, baseline);
""")

    def test_explicit_black_is_preserved_and_does_not_recolor_following_text(self) -> None:
        self.run_model(r"""
const field = new Field();
html(field, '<font color="#000000">Black</font> white');
assert.deepEqual(field.runs.map(run => run.format.color), [0, 0xFFFFFF]);
html(field, 'Normal again');
assert.equal(field.runs[0].format.color, 0xFFFFFF);
assert.equal(field.runs[0].format.font, '$EverywhereFont');
assert.equal(field.runs[0].format.size, 22);
""")

    def test_plain_text_preserves_literal_angle_brackets(self) -> None:
        self.run_model(r"""
const field = new Field();
html(field, '<font color="#FF0000">Previous</font>');
const literal = '<font color="#00FF00">Do not interpret</font> < 4 >';
plain(field, literal);
assert.equal(field.html, false);
assert.equal(field.text, literal);
assert.deepEqual(field.runs[0].format, baseline);
""")

    def test_null_undefined_and_non_string_values_use_safe_string(self) -> None:
        self.run_model(r"""
const field = new Field();
for (const value of [null, undefined]) {
    html(field, value);
    assert.equal(field.text, '');
    assert.deepEqual(field.next, baseline);
    plain(field, value);
    assert.equal(field.text, '');
    assert.equal(field.html, false);
}
html(field, 42);
assert.equal(field.text, '42');
plain(field, false);
assert.equal(field.text, 'false');
""")

    def test_uppercase_option_values_retain_markup_and_original_data(self) -> None:
        self.run_model(r"""
for (const optionType of [panel.OPTION_TEXT, panel.OPTION_MENU, panel.OPTION_INPUT]) {
    const entry = {optionType, text: '<font color="#123456">Label</font>',
        strValue: '<font color="#ab12cd">Mixed Case</font>', numValue: 0};
    const original = JSON.stringify(entry);
    const field = new Field({...baseline, align: 'right', size: 20});
    html(field, panel._formatOptionValue(entry));
    assert.equal(field.text, 'MIXED CASE');
    assert.equal(field.runs[0].format.color, 0xAB12CD);
    assert.equal(field.runs[0].format.align, 'right');
    assert.equal(JSON.stringify(entry), original);
    entry.strValue = '<font color="#11ee22">Updated</font>';
    const updated = JSON.stringify(entry);
    html(field, panel._formatOptionValue(entry));
    assert.equal(field.text, 'UPDATED');
    assert.equal(field.runs[0].format.color, 0x11EE22);
    assert.equal(JSON.stringify(entry), updated);
}
""")

    def test_slider_format_markup_survives_existing_value_formatting(self) -> None:
        self.run_model(r"""
const entry = {optionType: panel.OPTION_SLIDER,
    strValue: '<font color="#55aaee">{1} kg</font>', numValue: 12.25};
const original = JSON.stringify(entry);
const field = new Field();
html(field, panel._formatOptionValue(entry));
assert.equal(field.text, '12.3 KG');
assert.equal(field.runs[0].format.color, 0x55AAEE);
assert.equal(JSON.stringify(entry), original);
""")


if __name__ == "__main__":
    unittest.main()
