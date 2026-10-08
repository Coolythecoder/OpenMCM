"""Execute production AS2 extension bodies; not a Skyrim/Papyrus VM test."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import unittest

from test_formatted_text import body

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/actionscript/MCMCompatExtensions.as"
SIGNATURES = {
    "requestPage": ["host", "provider", "page", "token", "destination", "name"],
    "findPage": ["host", "destination", "name"],
    "drain": ["host"],
    "setOptionsEnabled": ["host", "provider", "page", "token", "enabled", "ids"],
}
SETUP = r"""
const assert=require('node:assert/strict');
const MCMCompatExtensions={};
for(const [name,method] of Object.entries(methods))
  MCMCompatExtensions[name]=new Function('scope',...method.args,
    'with(scope){'+method.body+'}').bind(null,MCMCompatExtensions);
function host(){return {
  READY:0,WAIT_FOR_SELECT:6,WAIT_FOR_DEFAULT:7,DIALOG:8,WAIT_FOR_OPTION_DATA:1,
  FOCUS_SIDE:0,_state:6,_openMCMApiEnabled:true,_dialog:null,_remapMode:false,
  _pageNames:[{pageIndex:0,pageName:'Main',enabled:true},
              {pageIndex:3,pageName:'$Advanced',enabled:true,text:'Advanced'}],
  _sideIndex:0,_focus:1,_requestPageReset:false,_openMCMNavigation:null,
  _provider:7,_page:0,_token:99,_events:[],_renders:0,
  _optionEntries:[{flags:0},{flags:2},{flags:4},{flags:7}],
  _openMCMMatchesPage(provider,page,token){return provider===this._provider &&
    page===this._page && token===this._token && token>0;},
  _openMCMOptionIndex(page,id){return Number.isInteger(id) && Math.floor(id/256)===page+1
    && id%256<this._optionEntries.length ? id%256:-1;},
  _selectPage(entry){this._events.push([entry.pageIndex,entry.pageName]);
    this._page=entry.pageIndex;this._token=0;this._state=1;this._openMCMNavigation=null;},
  _ensureSideVisible(){this._ensured=true;},_syncListInput(){},_focusActiveList(){},
  _renderOptions(){this._renders++;}
};}
const p=host(), e=MCMCompatExtensions;
"""


class BrowserExtensionTests(unittest.TestCase):
    def run_as2(self, assertions):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js required")
        source = SOURCE.read_text(encoding="utf-8")
        methods = {name: {"args": args, "body": re.sub(
            r"(\bvar\s+\w+)\s*:\s*\w+", r"\1", body(source, name))}
            for name, args in SIGNATURES.items()}
        result = subprocess.run([node, "-e", "const methods=" + json.dumps(methods)
                                 + ";\n" + SETUP + assertions],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_navigation_queues_until_unlock_and_updates_focus(self):
        self.run_as2("""
assert.equal(e.requestPage(p,7,0,99,3,'$Advanced'),true);
assert.deepEqual(p._events,[]);
assert.equal(e.drain(p),false);
p._state=p.READY;assert.equal(e.drain(p),true);
assert.deepEqual(p._events,[[3,'$Advanced']]);assert.equal(p._sideIndex,1);
assert.equal(p._focus,p.FOCUS_SIDE);assert.equal(p._ensured,true);
assert.equal(e.drain(p),false);
""")

    def test_ready_navigation_and_same_page_noop(self):
        self.run_as2("""
p._state=p.READY;
assert.equal(e.requestPage(p,7,0,99,0,'Main'),true);assert.deepEqual(p._events,[]);
assert.equal(e.requestPage(p,7,0,99,3,'$Advanced'),true);
assert.deepEqual(p._events,[[3,'$Advanced']]);
""")

    def test_navigation_rejects_unpublished_translated_or_missing_names(self):
        self.run_as2("""
for(const [idx,name] of [[1,'$Advanced'],[3,'Advanced'],[3,''],[3,'None'],[-1,''],[3.5,'$Advanced'],[NaN,'Main']])
  assert.equal(e.requestPage(p,7,0,99,idx,name),false);
p._pageNames[1].enabled=false;
assert.equal(e.requestPage(p,7,0,99,3,'$Advanced'),false);
assert.equal(p._openMCMNavigation,null);
""")

    def test_navigation_rejects_stale_wrong_provider_and_disabled_api(self):
        self.run_as2("""
for(const scope of [[7,0,0],[7,0,98],[8,0,99],[7,1,99]])
  assert.equal(e.requestPage(p,...scope,3,'$Advanced'),false);
p._openMCMApiEnabled=false;
assert.equal(e.requestPage(p,7,0,99,3,'$Advanced'),false);
""")

    def test_navigation_rejects_dialog_remap_and_building(self):
        self.run_as2("""
p._dialog={kind:'input'};assert.equal(e.requestPage(p,7,0,99,3,'$Advanced'),false);
p._dialog=null;p._remapMode=true;assert.equal(e.requestPage(p,7,0,99,3,'$Advanced'),false);
p._remapMode=false;p._state=p.WAIT_FOR_OPTION_DATA;
assert.equal(e.requestPage(p,7,0,99,3,'$Advanced'),false);
p._state=999;assert.equal(e.requestPage(p,7,0,99,3,'$Advanced'),false);
p._state=p.DIALOG;assert.equal(e.requestPage(p,7,0,99,3,'$Advanced'),true);
""")

    def test_delayed_navigation_revalidates_every_scope_and_destination(self):
        self.run_as2("""
for(const mutate of [p=>p._token=100,p=>p._provider=9,p=>p._page=2,
  p=>p._pageNames=[],p=>p._pageNames[1].pageName='Changed',p=>p._pageNames[1].enabled=false,
  p=>p._dialog={},p=>p._remapMode=true,p=>p._openMCMApiEnabled=false]){
  const q=host();assert.equal(e.requestPage(q,7,0,99,3,'$Advanced'),true);
  mutate(q);q._state=q.READY;assert.equal(e.drain(q),false);assert.deepEqual(q._events,[]);
  assert.equal(q._openMCMNavigation,null);
}
""")

    def test_navigation_reset_precedence(self):
        self.run_as2("""
p._requestPageReset=true;e.requestPage(p,7,0,99,3,'$Advanced');p._state=p.READY;
assert.equal(e.drain(p),true);assert.equal(p._requestPageReset,false);
const q=host();q._requestPageReset=true;e.requestPage(q,7,0,99,3,'$Advanced');
q._pageNames=[];q._state=q.READY;assert.equal(e.drain(q),false);
assert.equal(q._requestPageReset,true,'Invalid navigation must not swallow an ordinary reset');
""")

    def test_enable_groups_preserve_other_bits_and_repaint_once(self):
        self.run_as2("""
assert.equal(e.setOptionsEnabled(p,7,0,99,0,'256,257,258,259'),true);
assert.deepEqual(p._optionEntries.map(x=>x.flags),[1,3,5,7]);assert.equal(p._renders,1);
assert.equal(e.setOptionsEnabled(p,7,0,99,1,'256,257,258,259'),true);
assert.deepEqual(p._optionEntries.map(x=>x.flags),[0,2,4,6]);assert.equal(p._renders,2);
""")

    def test_group_validation_is_atomic_and_bounded(self):
        self.run_as2("""
for(const ids of ['', '256,999', '256,', '256,-1','256,256.5','0256','256,NaN',
 '256,Infinity',Array(129).fill('256').join(','),'2'.repeat(2049)]){
  assert.equal(e.setOptionsEnabled(p,7,0,99,0,ids),false,ids);
  assert.deepEqual(p._optionEntries.map(x=>x.flags),[0,2,4,7]);assert.equal(p._renders,0);
}
assert.equal(e.setOptionsEnabled(p,7,0,99,0,'256,256'),true);
assert.equal(p._renders,1);
""")

    def test_groups_require_enabled_api_and_current_scope(self):
        self.run_as2("""
for(const scope of [[7,0,0],[7,0,98],[8,0,99],[7,1,99]])
 assert.equal(e.setOptionsEnabled(p,...scope,0,'256'),false);
for(const enabled of [2,-1,NaN])assert.equal(e.setOptionsEnabled(p,7,0,99,enabled,'256'),false);
p._openMCMApiEnabled=false;assert.equal(e.setOptionsEnabled(p,7,0,99,0,'256'),false);
assert.equal(p._renders,0);
""")

    def test_sdk_exposes_scoped_capabilities_without_legacy_override(self):
        sdk = (ROOT / "src/papyrus/OpenMCM_ConfigBase.psc").read_text()
        discovery = (ROOT / "src/papyrus/OpenMCM.psc").read_text()
        self.assertIn('"page_navigation"', discovery)
        self.assertIn('"conditional_groups"', discovery)
        self.assertIn('Bool Function SetCurrentPage(String a_page, Int a_token)', sdk)
        self.assertIn('Bool Function SetOptionsEnabled(String[] a_keys, Bool a_enabled, Int a_token)', sdk)
        self.assertIn('OpenMCM_SendText("openMCMRequestPage"', sdk)
        self.assertIn('OpenMCM_SendText("openMCMSetOptionsEnabled"', sdk)

    def test_helper_states_match_real_panel_static_constants(self):
        panel = (ROOT / "src/actionscript/MCMCompatPanel.as").read_text()
        for name, value in {"READY": 0, "WAIT_FOR_SELECT": 6, "WAIT_FOR_DEFAULT": 7,
                            "DIALOG": 8, "FOCUS_SIDE": 0}.items():
            self.assertRegex(panel, rf"static var {name}:Number = {value};")


if __name__ == "__main__":
    unittest.main()
