"""Execute the actual AS2 extension method bodies with explicit UI stubs.

These are lifetime/transport tests, not a substitute for Scaleform or the native
AVM1 fixture. The normal build also compiles the complete production panel.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from test_formatted_text import body

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT / "src/actionscript/MCMCompatPanel.as"

METHODS = {
    "_invalidateOpenMCMPage": [], "_publishOpenMCMPage": [],
    "_getOpenMCMApiVersion": [], "_getOpenMCMPageToken": [],
    "_getOpenMCMApiEnabled": [], "setOpenMCMAPIEnabled": ["enabled"],
    "_getOpenMCMProviderID": [], "_getOpenMCMPageIndex": [],
    "_openMCMMatchesPage": ["provider", "page", "token"],
    "_openMCMOptionIndex": ["page", "fullID"],
    "openMCMSetOptionLabel": ["provider", "page", "token", "fullID", "text"],
    "openMCMSetOptionTextValue": ["provider", "page", "token", "fullID", "text"],
    "openMCMSetInfoText": ["provider", "page", "token", "fullID", "text"],
    "openMCMSetHighlightText": ["provider", "page", "token", "fullID", "text"],
    "_openMCMSetHelp": ["provider", "page", "token", "fullID", "text", "allowStatus"],
    "setInfoText": ["text"], "flushOptionBuffers": ["optionCount"],
    "setModNames": [], "setPageNames": [], "_selectPage": ["entry"],
    "_selectActivePage": [], "_goBack": [], "endPage": [], "onUnload": [],
}

MODEL = r"""
const assert = require('node:assert/strict');
globalThis._global = {};
globalThis.Mouse = {removeListener() {}};
globalThis.Key = {removeListener() {}};
globalThis.MCMCompatUtil = {
  safeString: value => value == null ? '' : String(value),
  translate: value => value == null ? '' : String(value),
  translateNested: value => value == null ? '' : String(value),
  sendModEvent: (...args) => events.push(args),
};
const events = [];
function panel(enabled = true) {
  const p = {OPTION_EMPTY:0, OPTION_TEXT:2, READY:0, WAIT_FOR_OPTION_DATA:1,
    FOCUS_SIDE:0, FOCUS_OPTIONS:1, _active:true, _visible:true,
    _sideMode:'pages', _selectedModRegistryIndex:7,
    _pageNames:[{pageIndex:0,pageName:'First'},{pageIndex:2,pageName:'Third'}],
    _activePageIndex:1, _sideIndex:1, _sideScroll:0, _focus:1,
    _optionIndex:24, _optionScrollRow:7, _highlightIndex:24,
    _optionEntries:Array.from({length:40}, () => ({optionType:2, flags:0, text:'Old',strValue:'old'})),
    _state:0, _dialog:null, _remapMode:false, _parent:{_visible:true},
    _modNames:[{modIndex:7,modName:'Author',text:'Author'}], _modList:{},
    _sideItems:[], _renders:0, _infoWrites:0, _openMCMPageReady:false, _openMCMApiEnabled:false,
    _openMCMPageToken:0, _highlightIntervalID:undefined, _remapDelayID:undefined, _infoText:'',
    _optionFlagsBuffer:[],_optionTextBuffer:[],_optionStrValueBuffer:[],_optionNumValueBuffer:[],
    _isVisibleAndActive() {return this._active && this._visible && this._parent._visible;},
    _renderOptions() {this._renders++;},
    _applyInfoText() {this._infoWrites++;},
    _applyTitleText() {}, _updateFooter() {}, _renderSide() {},
    _ensureSideVisible() {}, _focusActiveList() {}, _syncListInput() {},
    _stopModListRequest() {}, _closeDialog() {}, _setTextInputEnabled() {},
    _findModListIndex() {return 0;}, unloadCustomContent() {}, showWelcomeScreen() {},
  };
  p._sideItems = p._pageNames;
  for (const [name, definition] of Object.entries(methods))
    p[name] = new Function(...definition.params, 'with(this) {'+definition.body+'}');
  p.setOpenMCMAPIEnabled(enabled);
  p._publishOpenMCMPage();
  return p;
}
const p = panel();
const token = p._getOpenMCMPageToken();
const id = 3 * 256 + 24;
"""


class OpenMCMApiUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = PANEL.read_text(encoding="utf-8")

    def run_model(self, assertions: str) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is required for AS2 extension method tests")
        methods = {
            name: {"params": params, "body": re.sub(
                r"(\bvar\s+\w+)\s*:\s*\w+", r"\1", body(self.source, name))}
            for name, params in METHODS.items()
        }
        # setModNames's comparator is the only typed nested function used here.
        methods["setModNames"]["body"] = re.sub(
            r"function\(left:Object, right:Object\):Number", "function(left, right)",
            methods["setModNames"]["body"])
        result = subprocess.run(
            [node, "-e", "const methods=" + json.dumps(methods) + ";\n" + MODEL + assertions],
            text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_readonly_properties_installed_on_actual_mixin(self) -> None:
        initialize = body(self.source, "_initialize")
        for name in ("ApiVersion", "ApiEnabled", "PageToken", "ProviderID", "PageIndex"):
            self.assertIn(f'this.addProperty("openMCM{name}", this._getOpenMCM{name}, null)', initialize)
        self.assertIn("_openMCMApiEnabled = false;", initialize)

    def test_disabled_host_hides_api_and_rejects_public_updates(self) -> None:
        self.run_model(r"""
const off=panel(false), offToken=off._getOpenMCMPageToken();
assert.equal(off._getOpenMCMApiEnabled(),false);
assert.equal(off._getOpenMCMApiVersion(),0);
assert.ok(offToken>0,'Internal legacy help still requires published page identity');
assert.equal(off._getOpenMCMProviderID(),7);
assert.equal(off._getOpenMCMPageIndex(),2);
for(const method of ['openMCMSetOptionLabel','openMCMSetOptionTextValue','openMCMSetInfoText'])
  assert.equal(off[method](7,2,offToken,id,'Blocked'),false);
assert.equal(off.openMCMSetInfoText(7,2,offToken,-1,'Blocked status'),false);
assert.equal(off._optionEntries[24].text,'Old');
assert.equal(off._optionEntries[24].strValue,'old');
assert.equal(off._renders,0); assert.equal(off._infoWrites,0);
""")

    def test_toggle_invalidates_stale_work_until_flush_but_resync_is_idempotent(self) -> None:
        self.run_model(r"""
p.setOpenMCMAPIEnabled(true);
assert.equal(p._getOpenMCMPageToken(),token,'Idempotent enabled sync must preserve page');
p.setOpenMCMAPIEnabled(false);
assert.equal(p._getOpenMCMPageToken(),0);
assert.equal(p._getOpenMCMApiVersion(),0);
assert.equal(p.openMCMSetOptionLabel(7,2,token,id,'Stale'),false);
assert.equal(p.openMCMSetHighlightText(7,2,token,id,'Stale legacy'),false);
p.flushOptionBuffers(0);
const disabledToken=p._getOpenMCMPageToken();
assert.ok(disabledToken>token);
p.setOpenMCMAPIEnabled(false);
assert.equal(p._getOpenMCMPageToken(),disabledToken,'Idempotent disabled sync must preserve internal page');
p.setOpenMCMAPIEnabled(true);
assert.equal(p._getOpenMCMApiVersion(),1);
assert.equal(p._getOpenMCMPageToken(),0,'Re-enabling cannot resurrect old published scope');
assert.equal(p.openMCMSetInfoText(7,2,disabledToken,-1,'Stale'),false);
p.flushOptionBuffers(0);
assert.ok(p._getOpenMCMPageToken()>disabledToken);
assert.equal(p.openMCMSetInfoText(7,2,p._getOpenMCMPageToken(),-1,'Fresh'),true);
""")

    def test_explicit_legacy_help_survives_disabled_extensions_with_atomic_guards(self) -> None:
        self.run_model(r"""
const off=panel(false), offToken=off._getOpenMCMPageToken();
assert.equal(off.openMCMSetHighlightText(7,2,offToken,id,'Legacy help'),true);
assert.equal(off._infoText,'Legacy help');
assert.equal(off.openMCMSetHighlightText(7,2,offToken,-1,'Status bypass'),false);
assert.equal(off.openMCMSetHighlightText(8,2,offToken,id,'Wrong provider'),false);
assert.equal(off.openMCMSetHighlightText(7,1,offToken,id,'Wrong page'),false);
assert.equal(off.openMCMSetHighlightText(7,2,offToken+1,id,'Wrong token'),false);
assert.equal(off.openMCMSetHighlightText(7,2,offToken,24,'Wrong full ID'),false);
assert.equal(off.openMCMSetHighlightText(7,2,offToken,-2,''),false);
off._highlightIndex=25;
assert.equal(off.openMCMSetHighlightText(7,2,offToken,id,'Late help'),false);
assert.equal(off._infoText,'Legacy help');
off._highlightIndex=-1;
assert.equal(off.openMCMSetHighlightText(7,2,offToken,-2,''),true);
assert.equal(off._infoText,'');
""")

    def test_updates_preserve_navigation_and_formatted_source(self) -> None:
        self.run_model(r"""
const entries = p._optionEntries;
const before = [p._optionIndex,p._optionScrollRow,p._focus,p._highlightIndex,p._sideIndex,p._sideScroll];
const markup = '<font color="#00FF00">Ready</font>';
assert.equal(p.openMCMSetOptionLabel('7','2',String(token),String(id),markup),true);
assert.equal(p.openMCMSetOptionTextValue(7,2,token,id,markup),true);
assert.equal(p._optionEntries,entries);
assert.equal(entries[24].text,markup);
assert.equal(entries[24].strValue,markup);
assert.deepEqual([p._optionIndex,p._optionScrollRow,p._focus,p._highlightIndex,p._sideIndex,p._sideScroll],before);
assert.equal(p._getOpenMCMPageToken(),token);
assert.equal(p._renders,2);
assert.deepEqual(events,[]);
""")

    def test_invalid_provider_page_generation_and_ids_do_not_mutate(self) -> None:
        self.run_model(r"""
for(const args of [[8,2,token,id],[7,1,token,id],[7,2,token+1,id],[7,2,0,id],
  [7,2,token,24],[7,2,token,3*256+128],[7,2,token,3*256+40],
  [7,2,token,-1],[7,2,token,id+0.5],[7.1,2,token,id],
  [NaN,2,token,id],[7,Infinity,token,id],[7,2,Infinity,id],[7,2,token,Infinity]]) {
  assert.equal(p.openMCMSetOptionLabel(...args,'bad'),false,JSON.stringify(args));
  assert.equal(p.openMCMSetOptionTextValue(...args,'bad'),false,JSON.stringify(args));
}
p._optionEntries[24].optionType=0;
assert.equal(p.openMCMSetOptionLabel(7,2,token,id,'bad'),false);
assert.equal(p._renders,0);
assert.equal(p._optionEntries[24].text,'Old');
assert.equal(p._optionEntries[24].strValue,'old');
""")

    def test_text_value_rejects_other_legacy_types_but_labels_allow_them(self) -> None:
        self.run_model(r"""
for(const type of [1,3,4,5,6,7,8]) {
  p._optionEntries[24].optionType=type;
  assert.equal(p.openMCMSetOptionTextValue(7,2,token,id,'bad'),false);
  assert.equal(p.openMCMSetOptionLabel(7,2,token,id,'Allowed'),true);
}
assert.equal(p._optionEntries[24].strValue,'old');
""")

    def test_tooltips_must_still_belong_to_current_highlight(self) -> None:
        self.run_model(r"""
assert.equal(p.openMCMSetInfoText(7,2,token,id,'Current help'),true);
assert.equal(p._infoText,'Current help');
p._highlightIndex=25;
assert.equal(p.openMCMSetInfoText(7,2,token,id,'Late help'),false);
assert.equal(p._infoText,'Current help');
assert.equal(p.openMCMSetInfoText(7,2,token,-1,'Processing...'),true);
assert.equal(p._infoText,'Processing...');
assert.equal(p.openMCMSetInfoText(7,2,token,-1,''),true);
assert.equal(p._infoText,'');
assert.equal(p.openMCMSetInfoText(7,2,token+1,-1,'Stale'),false);
assert.equal(p.openMCMSetInfoText(7,2,token,NaN,'Bad'),false);
assert.equal(p.openMCMSetInfoText(7,2,token,-2,''),false);
p._highlightIndex=-1;
assert.equal(p.openMCMSetInfoText(7,2,token,-2,''),true);
assert.equal(p._infoText,'');
""")

    def test_zero_option_flush_creates_new_generation(self) -> None:
        self.run_model(r"""
p.flushOptionBuffers(0);
assert.ok(p._getOpenMCMPageToken()>token);
assert.equal(p.openMCMSetInfoText(7,2,token,-1,'Stale'),false);
assert.equal(p.openMCMSetInfoText(7,2,p._getOpenMCMPageToken(),-1,'Empty page status'),true);
""")

    def test_page_ready_status_paints_before_manager_unlock(self) -> None:
        self.run_model(r"""
p._state=p.WAIT_FOR_OPTION_DATA;
assert.equal(p.openMCMSetInfoText(7,2,token,-1,'Page ready'),true);
assert.equal(p._infoText,'Page ready');
assert.equal(p._infoWrites,1);
assert.equal(p._state,p.WAIT_FOR_OPTION_DATA,'Status must not prematurely unlock page');
""")

    def test_generations_are_not_reused_by_panel_recreation(self) -> None:
        self.run_model(r"""
p.onUnload();
assert.equal(p._getOpenMCMPageToken(),0);
const second=panel();
assert.ok(second._getOpenMCMPageToken()>token);
assert.equal(second.openMCMSetOptionLabel(7,2,token,id,'Stale'),false);
""")

    def test_provider_registry_refresh_does_not_invalidate_page(self) -> None:
        self.run_model(r"""
p.setModNames('Zebra','','Author');
assert.equal(p._getOpenMCMPageToken(),token);
assert.equal(p._sideMode,'pages');
assert.equal(p._optionEntries.length,40);
assert.equal(p.openMCMSetOptionLabel(7,2,token,id,'Fresh'),true);
""")

    def test_page_list_refresh_preserves_raw_identity_or_invalidates(self) -> None:
        self.run_model(r"""
p.setPageNames('First','None','Third');
assert.equal(p._getOpenMCMPageToken(),token);
assert.equal(p._getOpenMCMPageIndex(),2);
p.setPageNames('First','None','Replacement');
assert.equal(p._getOpenMCMPageToken(),0);
assert.equal(p.openMCMSetInfoText(7,2,token,-1,'Stale'),false);
""")

    def test_navigation_invalidates_before_page_request(self) -> None:
        self.run_model(r"""
p._selectPage(p._pageNames[0]);
assert.equal(p._getOpenMCMPageToken(),0);
assert.equal(p.openMCMSetOptionLabel(7,2,token,id,'Stale'),false);
assert.equal(events[0][0],'SKICP_pageSelected');
assert.equal(events[0][2],0);
const other=panel(); other._selectActivePage();
assert.equal(other._getOpenMCMPageToken(),0);
""")

    def test_back_hides_scope_even_without_provider_close(self) -> None:
        self.run_model(r"""
p._goBack();
assert.equal(p._sideMode,'mods');
assert.equal(p._getOpenMCMPageToken(),0);
assert.equal(p._getOpenMCMProviderID(),-1);
assert.equal(p._getOpenMCMPageIndex(),-2);
assert.equal(p.openMCMSetInfoText(7,2,token,-1,'Stale'),false);
""")

    def test_end_and_hidden_panel_reject_updates(self) -> None:
        self.run_model(r"""
p._parent._visible=false;
assert.equal(p._getOpenMCMPageToken(),0);
assert.equal(p.openMCMSetOptionLabel(7,2,token,id,'Hidden'),false);
p._parent._visible=true;
p.endPage();
assert.equal(p._getOpenMCMPageToken(),0);
assert.equal(p.openMCMSetInfoText(7,2,token,-1,'Closed'),false);
""")

    def test_blank_initial_page_is_distinct_from_first_named_page(self) -> None:
        self.run_model(r"""
p._activePageIndex=-1;
assert.equal(p._getOpenMCMPageIndex(),-1);
assert.equal(p.openMCMSetOptionLabel(7,-1,token,24,'Blank'),true);
assert.equal(p.openMCMSetOptionLabel(7,0,token,256+24,'Wrong'),false);
""")

    def test_token_exhaustion_fails_closed_without_reuse(self) -> None:
        self.run_model(r"""
_global.OpenMCM_APIPageSerial=2147483647;
p._invalidateOpenMCMPage();p._publishOpenMCMPage();
assert.equal(p._getOpenMCMPageToken(),0);
""")

    def test_all_lifecycle_paths_invalidate_and_updates_never_reset(self) -> None:
        for name in ("startPage", "endPage", "onUnload", "_goBack", "_selectMod", "_selectPage", "_selectActivePage", "flushOptionBuffers"):
            self.assertIn("_invalidateOpenMCMPage();", body(self.source, name), name)
        for name in ("openMCMSetOptionLabel", "openMCMSetOptionTextValue", "openMCMSetInfoText"):
            method = body(self.source, name)
            self.assertNotIn("flushOptionBuffers", method)
            self.assertNotIn("forcePageReset", method)
            self.assertNotIn("sendModEvent", method)


if __name__ == "__main__":
    unittest.main()
