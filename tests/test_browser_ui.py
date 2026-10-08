"""Run production AS2 browser method bodies in Node with explicit host stubs.

These validate preferences, filtering and bridge transactions, not game input,
font layout, Papyrus scheduling or Scaleform. MTASC compiles the full UI too.
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
SOURCE = ROOT / "src/actionscript/MCMCompatBrowser.as"
PANEL = ROOT / "src/actionscript/MCMCompatPanel.as"
METHODS = {
    "bridge": [], "clamp": ["value", "minimum", "maximum"],
    "preference": ["name", "create"], "find": ["name"],
    "receive": ["list"], "filtered": [], "selected": ["entry"],
    "captureScroll": [], "restoreScroll": [], "rebuild": ["resetScroll"],
    "buildState": [], "loadState": ["serialized"], "hasRecoveryMarker": ["serialized"], "loadNative": [],
    "loadSavedGame": ["serialized"], "save": [], "action": ["actionName"],
    "accept": ["actionName", "name", "value"],
}

MODEL = r"""
const assert = require('node:assert/strict');
globalThis._global = {};
globalThis._root = {};
const events = [];
globalThis.MCMCompatUtil = {sendModEvent(...args) {events.push(args);}};
function browser() {
  const owner = {_sideMode:'mods',_state:0,_dialog:null,_modNames:[],_sideIndex:-1,
    _modList:{entryList:[],scrollPosition:0,visibleCount:18},
    _isVisibleAndActive() {return true;}, _renderSide() {}, _updateFooter() {},
    _openBrowserInput(...args) {this.input=args;}, _openBrowserTools() {this.tools=true;}};
  const b = {owner,entries:[],preferences:[],sorts:[0,0,0],scrolls:[0,0,0],
    bottoms:[false,false,false],tab:0,query:'',targetName:'',nativeLoaded:false,
    preferencesLoaded:false,registryReceived:false,recoveryPending:false,
    locallyChanged:false,lastSaved:'',storageStatus:'Saved with this character',
    render() {}};
  for(const [name, method] of Object.entries(methods))
    b[name]=new Function(...method.params,'with(this) {'+method.body+'}');
  return b;
}
function menus(...names) {
  return names.map((name,index)=>({modName:name,text:name,modIndex:index*7,enabled:true}));
}
function receive(b,list,acknowledge=true) {
  // Normal manager order is loadBrowserState, then setModNames. Race cases
  // explicitly opt out to deliver the registry before its preference reply.
  if(acknowledge)b.loadSavedGame('');
  b.owner._modNames=b.receive(list);
  b.owner._modList.entryList=b.owner._modNames;
}
function fakeNative(initial='') {
  let committed=initial, pending='';
  const calls=[];
  const bridge={calls,
    GetProfileStateChunkCount() {return Math.ceil(committed.length/1024);},
    GetProfileStateChunk(i) {return committed.slice(i*1024,(i+1)*1024);},
    BeginProfileStateUpdate() {calls.push('begin');pending='';return true;},
    AppendProfileStateChunk(v) {calls.push(['append',v]);pending+=v;return true;},
    CommitProfileStateUpdate() {calls.push('commit');committed=pending;return true;},
    state() {return committed;}};
  _global.skse={plugins:{OpenMCMBrowser:bridge}};
  return bridge;
}
const b=browser();
"""


class BrowserUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_text(encoding="utf-8")
        cls.panel = PANEL.read_text(encoding="utf-8")

    def run_methods(self, assertions):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for AS2 browser method tests")
        methods = {}
        for name, params in METHODS.items():
            implementation = re.sub(r"(\bvar\s+\w+)\s*:\s*\w+", r"\1", body(self.source, name))
            implementation = re.sub(r"function\(left:Object, right:Object\):Number",
                                    "function(left,right)", implementation)
            methods[name] = {"params": params, "body": implementation}
        result = subprocess.run([node, "-e", "const methods=" + json.dumps(methods) + ";" + MODEL + assertions],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_original_sparse_ids_survive_search_sort_and_rename(self):
        self.run_methods("""
receive(b,menus('Zulu','alpha','XPMSE'));
b.accept('rename','Zulu','Aardvark');
assert.deepEqual(b.filtered().map(e=>e.modIndex),[0,7,14]);
b.accept('search','','zulu');
assert.equal(b.filtered()[0].modName,'Zulu');
assert.equal(b.filtered()[0].modIndex,0);
assert.equal(b.filtered()[0].text,'Aardvark');
assert.equal(b.entries[0].text,'Zulu');
""")

    def test_search_matches_localized_original_alias_and_raw_name(self):
        self.run_methods("""
receive(b,[{modName:'$RAW_MCM',text:'Translated',modIndex:93}]);
b.accept('rename','$RAW_MCM','Custom');
for(const q of ['raw_mcm','TRANSLATED','custom']) {
 b.accept('search','',q);assert.equal(b.filtered().length,1);
}
b.accept('search','','missing');assert.deepEqual(b.filtered(),[]);
""")

    def test_favorites_and_hidden_are_independent_and_recoverable(self):
        self.run_methods("""
receive(b,menus('A','B')); b.selected(b.entries[1]);
b.action('favorite');b.action('favorites');assert.equal(b.filtered()[0].modName,'B');
b.action('hide');assert.equal(b.filtered().length,0);
b.action('all');assert.deepEqual(b.filtered().map(e=>e.modName),['A']);
b.action('hidden');assert.equal(b.filtered()[0].modName,'B');
b.action('hide');b.action('favorites');assert.equal(b.filtered()[0].modName,'B');
assert.equal(b.entries.length,2);
""")

    def test_priority_precedes_all_sort_modes(self):
        self.run_methods("""
receive(b,menus('Z','B','A'));b.accept('priority','Z','1');
assert.deepEqual(b.filtered().map(e=>e.modName),['Z','A','B']);
b.action('sort');assert.deepEqual(b.filtered().map(e=>e.modName),['Z','B','A']);
b.action('sort');assert.deepEqual(b.filtered().map(e=>e.modName),['Z','B','A']);
b.accept('priority','Z','0');b.action('sort');
assert.deepEqual(b.filtered().map(e=>e.modName),['A','B','Z']);
""")

    def test_alias_empty_restores_original_and_bounded_inputs(self):
        self.run_methods("""
receive(b,menus('Original'));b.accept('rename','Original','New');
b.accept('rename','Original','');assert.equal(b.filtered()[0].text,'Original');
b.accept('rename','Original','x'.repeat(100));assert.equal(b.filtered()[0].text.length,60);
b.accept('priority','Original','2000');assert.equal(b.filtered()[0].priority,999);
b.accept('priority','Original','NaN');assert.equal(b.filtered()[0].priority,1000000);
""")

    def test_atomic_invalid_profile_does_not_overwrite_working_data(self):
        self.run_methods("""
receive(b,menus('A'));b.accept('rename','A','Good');const before=b.buildState();
for(const bad of ['MCMR1|0|0|0|0|0|0|0|0|0|0',before+'|N|A',before+'|X|A',
 before+'|N||Alias',before+'|N|A|'+escape('x'.repeat(61)),'x'.repeat(32769)]) {
 assert.equal(b.loadState(bad),false);assert.equal(b.buildState(),before);
}
""")

    def test_round_trip_unicode_delimiters_and_prototype_names(self):
        self.run_methods("""
receive(b,menus('__proto__','日本語|MCM%','constructor'));
for(const e of b.entries) {b.selected(e);b.action('favorite');b.accept('rename',e.modName,'É|%😀');}
b.action('hidden');const state=b.buildState();const next=browser();
assert.equal(next.loadState(state),true);assert.equal(next.buildState(),state);
assert.equal(next.preference('__proto__',false).alias,'É|%😀');
""")

    def test_missing_menus_keep_preferences_without_creating_fake_entries(self):
        self.run_methods("""
receive(b,menus('A','B'));b.selected(b.entries[1]);b.action('favorite');
receive(b,menus('A'));const state=b.buildState();assert.ok(state.includes('|F|B'));
assert.equal(b.filtered().length,1);receive(b,menus('A','B'));
b.action('favorites');assert.equal(b.filtered()[0].modName,'B');
""")

    def test_preferences_can_outlive_more_than_one_128_menu_load_order(self):
        self.run_methods("""
for(let i=0;i<300;i++) b.preference('Historical '+i,true).favorite=true;
receive(b,menus('Current'));b.selected(b.entries[0]);b.action('favorite');
assert.equal(b.preference('Current',false).favorite,true);
const state=b.buildState();assert.ok(state.length<32768);
const next=browser();assert.equal(next.loadState(state),true);
assert.equal(next.preferences.length,301);
""")

    def test_search_does_not_overwrite_remembered_scroll(self):
        self.run_methods("""
receive(b,menus(...Array.from({length:30},(_,i)=>String(i))));
b.owner._modList.scrollPosition=12;b.captureScroll();assert.equal(b.bottoms[0],true);
b.accept('search','','1');b.owner._modList.scrollPosition=0;b.captureScroll();
assert.equal(b.scrolls[0],12);b.action('clear');assert.equal(b.owner._modList.scrollPosition,12);
""")

    def test_save_local_fallback_without_native_and_late_load_cannot_undo_edit(self):
        self.run_methods("""
receive(b,menus('A'));const old=b.buildState();b.selected(b.entries[0]);b.action('favorite');
assert.equal(events[0][0],'OPENMCM_browserStateChanged');assert.ok(events[0][1].includes('|F|A'));
b.loadSavedGame(old);assert.equal(b.preference('A',false).favorite,true);
""")

    def test_untouched_close_before_handshake_cannot_publish_defaults(self):
        self.run_methods("""
b.save();assert.equal(events.length,0);assert.equal(b.locallyChanged,false);
receive(b,menus('Existing'),false);b.save();assert.equal(events.length,0);
b.loadSavedGame('OPENMCMB1|0|0|0|0|0|0|0|0|0|0|F|Existing');
assert.equal(b.preference('Existing',false).favorite,true);b.save();
assert.equal(events.length,0);
""")

    def test_native_preference_scroll_survives_early_close_before_registry(self):
        self.run_methods("""
const stored='OPENMCMB1|0|0|0|0|9|0|0|0|0|0|F|Existing';
const native=fakeNative(stored);b.loadNative();b.save();
assert.equal(native.state(),stored);assert.equal(b.scrolls[0],9);
assert.equal(native.calls.length,0);assert.equal(events.length,0);
b.loadSavedGame('');receive(b,[]);b.save();
assert.equal(native.state(),stored);assert.equal(b.scrolls[0],9);
""")

    def test_empty_manager_handshake_then_real_scrolling_is_persisted(self):
        self.run_methods("""
b.loadSavedGame('');b.save();assert.equal(events.length,0);
receive(b,menus(...Array.from({length:40},(_,i)=>'Mod '+i)));
b.owner._modList.scrollPosition=8;b.save();
assert.equal(events.length,1);assert.equal(b.scrolls[0],8);
assert.equal(events[0][1].split('|')[5],'8');
""")

    def test_early_actions_cannot_discard_unknown_saved_history(self):
        self.run_methods("""
b.action('favorites');b.accept('rename','Old','New');
assert.equal(events.length,0);assert.equal(b.tab,0);
b.loadSavedGame('OPENMCMB1|0|0|0|0|0|0|0|0|0|0|F|Old');
b.action('favorites');assert.equal(b.tab,1);assert.equal(events.length,1);
assert.equal(b.preference('Old',false).favorite,true);
""")

    def test_native_profile_does_not_enable_actions_before_local_recovery_reply(self):
        self.run_methods("""
fakeNative('OPENMCMB1|0|0|0|0|0|0|0|0|0|0|N|A|Shared');b.loadNative();
assert.equal(b.preferencesLoaded,false);receive(b,menus('A'),false);
b.accept('rename','A','Too early');b.action('favorites');assert.equal(events.length,0);
b.loadSavedGame('OPENMCMB1|0|0|0|0|0|0|0|0|0|0|N|A|Recovered|L|1');
assert.equal(b.preference('A',false).alias,'Recovered');assert.equal(b.preferencesLoaded,true);
""")

    def test_invalid_manager_state_acknowledges_without_automatic_overwrite(self):
        self.run_methods("""
receive(b,menus('A'),false);b.loadSavedGame('BROKEN');
assert.equal(b.preferencesLoaded,true);assert.ok(b.storageStatus.includes('invalid'));
b.save();assert.equal(events.length,0);b.action('favorites');assert.equal(events.length,1);
""")

    def test_search_and_menu_open_are_not_persistent_edits_before_handshake(self):
        self.run_methods("""
b.action('search');b.accept('search','','temporary');b.action('clear');b.action('tools');b.save();
assert.equal(events.length,0);assert.equal(b.locallyChanged,false);
""")

    def test_failed_native_commit_recovery_survives_a_new_movie(self):
        self.run_methods("""
const old='OPENMCMB1|0|0|0|0|0|0|0|0|0|0|N|A|Old';
const native=fakeNative(old);native.CommitProfileStateUpdate=()=>false;
b.loadNative();receive(b,menus('A'));b.accept('rename','A','New');
const fallback=events.at(-1)[1];assert.ok(fallback.endsWith('|L|1'));
assert.equal(native.state(),old);const next=browser();next.loadNative();
assert.equal(next.preference('A',false).alias,'Old');next.loadSavedGame(fallback);
assert.equal(next.preference('A',false).alias,'New');assert.equal(next.recoveryPending,true);
""")

    def test_recovery_retry_without_changes_clears_marker_only_after_success(self):
        self.run_methods("""
const native=fakeNative();const commit=native.CommitProfileStateUpdate;
native.CommitProfileStateUpdate=()=>false;
receive(b,menus('A'));b.accept('rename','A','New');
assert.ok(events.at(-1)[1].endsWith('|L|1'));const first=events.length;
b.save();assert.equal(events.length,first+1);assert.equal(b.recoveryPending,true);
native.CommitProfileStateUpdate=commit;b.save();
assert.equal(b.recoveryPending,false);assert.ok(!events.at(-1)[1].endsWith('|L|1'));
assert.ok(!native.state().includes('|L|1'));assert.equal(native.state(),b.buildState());
const count=events.length;b.save();assert.equal(events.length,count);
""")

    def test_recovery_marker_survives_missing_bridge_and_stale_unmarked_reply(self):
        self.run_methods("""
const recovery='OPENMCMB1|0|0|0|0|0|0|0|0|0|0|N|A|Recovered|L|1';
b.loadSavedGame(recovery);b.loadSavedGame('');
assert.equal(b.preference('A',false).alias,'Recovered');
b.save();assert.equal(events.at(-1)[1],recovery);assert.equal(b.recoveryPending,true);
assert.ok(b.storageStatus.includes('unavailable'));
""")

    def test_recovery_marker_is_transactionally_validated_and_not_a_native_profile(self):
        self.run_methods("""
const good='OPENMCMB1|0|0|0|0|0|0|0|0|0|0|F|A';
b.loadState(good);for(const bad of [good+'|L|0',good+'|L',good+'|L|1|L|1',good+'|L|1|F|B']) {
 assert.equal(b.loadState(bad),false);assert.equal(b.buildState(),good);assert.equal(b.recoveryPending,false);
}
fakeNative(good+'|L|1');const next=browser();next.loadNative();
assert.equal(next.nativeLoaded,false);assert.equal(next.preferencesLoaded,false);
""")

    def test_recovery_marker_budget_boundary_is_reserved_before_any_write(self):
        self.run_methods("""
const native=fakeNative();native.CommitProfileStateUpdate=()=>false;
b.loadSavedGame('');b.locallyChanged=true;b.buildState=()=>'X'.repeat(32764);b.save();
assert.equal(events.at(-1)[1].length,32768);assert.ok(events.at(-1)[1].endsWith('|L|1'));
const count=events.length,calls=native.calls.length;
b.buildState=()=>'X'.repeat(32765);b.save();
assert.equal(events.length,count);assert.equal(native.calls.length,calls);
assert.equal(b.storageStatus,'Preferences too large to save');
""")

    def test_fallback_is_not_published_until_native_commit_result_is_known(self):
        self.run_methods("""
const native=fakeNative();const commit=native.CommitProfileStateUpdate;
native.CommitProfileStateUpdate=()=>{assert.equal(events.length,0);return commit();};
receive(b,menus('A'));b.selected(b.entries[0]);b.action('favorite');
assert.equal(events.length,1);assert.ok(!events[0][1].endsWith('|L|1'));
""")

    def test_native_loaded_profile_beats_old_save(self):
        self.run_methods("""
receive(b,menus('A'));const older=b.buildState();b.selected(b.entries[0]);b.action('favorite');
fakeNative(b.buildState());const next=browser();next.loadNative();
assert.equal(next.nativeLoaded,true);next.loadSavedGame(older);
assert.equal(next.preference('A',false).favorite,true);
""")

    def test_empty_native_profile_accepts_save_fallback(self):
        self.run_methods("""
fakeNative();b.loadNative();assert.equal(b.nativeLoaded,false);
b.loadSavedGame('OPENMCMB1|1|0|0|0|0|0|0|0|0|0|F|Existing');
assert.equal(b.preference('Existing',false).favorite,true);assert.equal(b.tab,1);
""")

    def test_chunked_write_is_ordered_bounded_and_deduplicated(self):
        self.run_methods("""
const native=fakeNative();receive(b,menus(...Array.from({length:30},(_,i)=>'Mod '+i)));
b.loadSavedGame('');
for(const e of b.entries)b.preference(e.modName,true).alias='x'.repeat(60);
b.save();assert.equal(native.calls[0],'begin');assert.equal(native.calls.at(-1),'commit');
assert.ok(native.calls.filter(Array.isArray).length>1);
assert.ok(native.calls.filter(Array.isArray).every(c=>c[1].length<=1024));
assert.equal(native.state(),b.buildState());const count=native.calls.length;b.save();
assert.equal(native.calls.length,count);assert.equal(events.length,1);
""")

    def test_failed_native_chunk_never_commits_but_retains_fallback(self):
        self.run_methods("""
const native=fakeNative();native.AppendProfileStateChunk=()=>false;
receive(b,menus('A'));b.selected(b.entries[0]);b.action('favorite');
assert.ok(!native.calls.includes('commit'));assert.equal(events.length,1);
assert.ok(b.storageStatus.includes('failed'));assert.equal(b.nativeLoaded,false);
""")

    def test_native_invalid_chunk_count_and_oversized_data_are_ignored(self):
        self.run_methods("""
const native=fakeNative();for(const count of [-1,0,33,1.5,NaN]) {
 native.GetProfileStateChunkCount=()=>count;b.loadNative();assert.equal(b.nativeLoaded,false);
}
native.GetProfileStateChunkCount=()=>1;native.GetProfileStateChunk=()=>false;
b.loadNative();assert.equal(b.nativeLoaded,false);
native.GetProfileStateChunk=()=>'x'.repeat(1025);b.loadNative();assert.equal(b.nativeLoaded,false);
""")

    def test_actions_do_not_mutate_an_open_provider_or_dialog(self):
        self.run_methods("""
receive(b,menus('A'));b.selected(b.entries[0]);const before=b.buildState();
b.owner._sideMode='pages';b.action('favorite');assert.equal(b.buildState(),before);
b.owner._sideMode='mods';b.owner._dialog={};b.action('hide');assert.equal(b.buildState(),before);
b.owner._dialog=null;b.owner._state=1;b.action('sort');assert.equal(b.buildState(),before);
""")

    def test_menu_refresh_uses_raw_identity_not_old_position(self):
        self.run_methods("""
receive(b,menus('A','B'));b.selected(b.entries[1]);b.action('favorite');
receive(b,[{modName:'B',text:'B',modIndex:100},{modName:'A',text:'A',modIndex:1}]);
b.action('favorites');assert.equal(b.filtered()[0].modIndex,100);
""")

    def test_duplicate_names_have_shared_presentation_preferences(self):
        self.run_methods("""
receive(b,[{modName:'Same',text:'Same',modIndex:3},{modName:'Same',text:'Same',modIndex:90}]);
b.accept('rename','Same','Shared');assert.equal(b.filtered().length,2);
assert.deepEqual(b.filtered().map(e=>e.modIndex),[3,90]);
assert.ok(b.filtered().every(e=>e.text==='Shared'));
""")

    def test_browser_dialogs_do_not_emit_provider_callbacks(self):
        for name in ["_acceptDialog", "_cancelDialog"]:
            implementation = body(self.panel, name)
            self.assertLess(implementation.index("browserAction"), implementation.index("SKICP_"))
        self.assertIn("sendCancel && !browserDialog", body(self.panel, "_closeDialog"))
        self.assertIn("if (browserDialog) _state = READY", body(self.panel, "_closeDialog"))

    def test_new_controls_leave_mouse_dispatch_owned_by_existing_lists(self):
        self.assertNotIn("Mouse.addListener", self.source)
        self.assertNotIn("Key.addListener", self.source)
        self.assertNotIn("setInterval", self.source)
        self.assertIn("this._browser.selected(event.entry)", body(self.panel, "_onListSelectionChange"))
        self.assertIn("_selectMod(event.entry)", body(self.panel, "_onListPress"))


if __name__ == "__main__":
    unittest.main()
