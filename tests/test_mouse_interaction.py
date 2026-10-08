"""Actual panel callback and modal renderer contracts, not Scaleform mocks.

List lifetime/event ownership is exercised in test_list_component.py. Native
mouse hit dispatch and complete panel interaction run in tests/avm1 --flow.
"""
from __future__ import annotations
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path
from test_text_input_ownership import body

PANEL = Path(__file__).resolve().parents[1] / "src/actionscript/MCMCompatPanel.as"


def methods(source: str, names: tuple[str, ...]) -> dict:
    result = {}
    for name in names:
        match = re.search(rf"function\s+{name}\(([^)]*)\):\w+", source)
        if match is None:
            raise AssertionError(f"missing function {name}")
        code = re.sub(r"(\bvar\s+\w+)\s*:\s*\w+", r"\1", body(source, name))
        code = re.sub(r"(function\s*\()([^)]*)(\))", lambda m: m.group(1) + re.sub(r":\w+", "", m.group(2)) + m.group(3), code)
        code = re.sub(r"(function\s*\([^)]*\)):\w+", r"\1", code)
        result[name] = {"params": re.sub(r":\w+", "", match.group(1)), "body": code}
    return result


class MouseInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = PANEL.read_text(encoding="utf-8")

    def run_js(self, program: str) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is needed to execute AS2 mouse methods")
        run = subprocess.run([node, "-"], input=program, text=True, capture_output=True, timeout=20)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_panel_uses_persistent_lists_and_ordinary_transparent_geometry(self) -> None:
        for name in ("_renderSide", "_renderOptions"):
            render = body(self.source, name)
            for token in (".beginUpdate();", ".getRenderer(", ".endUpdate();", "trigger._visible = true;"):
                self.assertIn(token, render)
            for token in ("row.onPress =", "row.onRollOver =", "row.hitArea =", "removeMovieClip", "trigger._visible = false;"):
                self.assertNotIn(token, render)
        for name in ("_modList", "_pageList", "_optionsList"):
            self.assertIn(name + " = MCMCompatList.install(", self.source)
        self.assertIn("onItemPress = this._onListPress", self.source)
        self.assertIn("onSelectionChange = this._onListSelectionChange", self.source)
        press = body(self.source, "_onListPress")
        self.assertNotIn("_activateCurrent", press)
        self.assertNotIn("_sideIndex", press)

    def test_list_events_keep_origin_and_identity_through_panel_dispatch(self) -> None:
        program = "const methods = " + json.dumps(methods(self.source, ("_onListPress", "_onListSelectionChange"))) + ";\n" + r"""
const assert = require('node:assert/strict');
globalThis.READY=0; globalThis.FOCUS_OPTIONS=1; globalThis.FOCUS_SIDE=0;
function panel() {
 const p={_active:true,_dialog:null,_remapMode:false,_state:READY,_focus:1,_sideIndex:900,calls:[],
  _noteMouseEvent(...args){this.calls.push(['note',...args]);},
  _selectMod(entry){this.calls.push(['mod',entry]);},
  _selectPage(entry){this.calls.push(['page',entry]);},
  _selectOption(index){this.calls.push(['option',index]);},
  _focusComponent(target){this.focused=target;this._sideIndex=-1;},
  _initHighlight(index){this.highlight=index;},
  _refreshSideSelection(){},_refreshOptionSelection(){},_updateFooter(){}};
 for(const [name,code] of Object.entries(methods)) p[name]=new Function(code.params,'with(this){'+code.body+'}');
 return p;
}
for(const [kind,verb,entry,index] of [['mods','mod',{modIndex:91},4],['pages','page',{pageIndex:17,pageName:'Styles'},1],['options','option',{optionType:3},10]]) {
 const p=panel(),list={kind},event={kind,list,entry,index};
 p._onListSelectionChange(event); assert.equal(p.focused,list);
 assert.equal(p._focus,kind==='options'?FOCUS_OPTIONS:FOCUS_SIDE);
 p._onListPress(event); assert.deepEqual(p.calls.at(-1),[verb,kind==='options'?index:entry]);
}
for(const guard of ['inactive','dialog','remap','waiting']) {
 const p=panel();
 if(guard==='inactive')p._active=false;
 if(guard==='dialog')p._dialog={kind:'menu'};
 if(guard==='remap')p._remapMode=true;
 if(guard==='waiting')p._state=1;
 for(const kind of ['mods','pages','options'])p._onListPress({kind,index:0,entry:{}});
 assert.deepEqual(p.calls,[]);
}
"""
        self.run_js(program)

    def test_actual_slider_callbacks_preserve_drag_target(self) -> None:
        names = ("_renderSliderDialog", "_refreshSlider",
                 "_makeSliderArrow", "_adjustSlider", "_adjustSliderPage", "_lockSliderValue",
                 "_setSliderFromMouse", "onMouseMove", "onMouseUp", "_dialogAction")
        constants = dict(re.findall(r"(?:public|private) static var (\w+):Number = ([\d.]+);", self.source))
        program = "const methods=" + json.dumps(methods(self.source, names)) + ";\nconst constants=" + json.dumps(constants) + ";\n" + r"""
const assert=require('node:assert/strict');
for(const [name,value]of Object.entries(constants))globalThis[name]=Number(value);
function clip(parent,name){return{_parent:parent,_name:name,children:{},graphics:[],_visible:true,
 clear(){assert.equal(this.removed,undefined);this.graphics=[];},
 removeMovieClip(){this.removed=true;if(parent)delete parent[name];},
 createEmptyMovieClip(n,depth){const c=clip(this,n);c.depth=depth;this.children[n]=this[n]=c;return c;}};}
function field(parent,name,depth,x,y,w,h){const f={_x:x,_y:y,_width:w,_height:h,text:'',textWidth:20,
 getNewTextFormat(){return{};},setNewTextFormat(){},setTextFormat(){},getLineMetrics(){return{width:this.textWidth,x:1};}};
 parent.children[name]=parent[name]=f;return f;}
globalThis.MCMCompatUtil={makeText:field,safeString:x=>String(x??''),translate:x=>x,
 applyText:(f,x)=>{f.text=String(x);},applyHtmlText:(f,x)=>{f.text=String(x);},applyDropShadow(){},formatSlider:(f,v)=>String(v)};
for(const name of ['drawHorizontalGradientRect','drawRadialGradientRect','drawCenteredGradientRect','drawPolygon','drawDiamond','drawLine','drawRect'])
 MCMCompatUtil[name]=(target,...args)=>{assert.equal(target.removed,undefined);target.graphics.push({name,args});};
function panel(){const p={_chrome:clip(null,'chrome'),_dialog:null,_sliderDragging:false,
 _placeLeftButton(){},_placeRightButton(){},_placeRightButtons(){},_focusComponent(target){this.focused=target;},_acceptDialog(){this.accepted=true;},
 _cancelDialog(){this.cancelled=true;},_renderDialog(){throw Error('Visual-only change rebuilt modal layer');}};
 p._modalLayer=p._chrome.createEmptyMovieClip('modalLayer',100);
 for(const[name,code]of Object.entries(methods))p[name]=new Function(code.params,'with(this){'+code.body+'}');return p;}
function sameTarget(t,p,n,label){assert.equal(t.removed,undefined);assert.equal(p[n],t);if(label)assert.equal(t.label,label);}
let p=panel();p._dialog={kind:'slider',minimum:0,maximum:100,interval:5,value:20,defaultValue:25,format:'{0}'};p._renderSliderDialog();
const sliderModal=p._modalLayer,track=sliderModal.sliderTrack;
assert.equal(p.focused,track);
track._xmouse=SLIDER_TRACK_X+SLIDER_TRACK_W*0.5;track.onPress();assert.equal(p._dialog.value,50);assert.equal(p._sliderDragging,true);sameTarget(track,sliderModal,'sliderTrack');
p._xmouse=SLIDER_TRACK_X+SLIDER_TRACK_W*0.8;p.onMouseMove();assert.equal(p._dialog.value,80);sameTarget(track,sliderModal,'sliderTrack');
track._xmouse=SLIDER_TRACK_X+SLIDER_TRACK_W;track.onRelease();assert.equal(p._dialog.value,100);assert.equal(p._sliderDragging,false);assert.equal(sliderModal.sliderValue.text,'100');
sliderModal.sliderMinus.onPress();assert.equal(p._dialog.value,95);p._dialogAction('sliderDefault');assert.equal(p._dialog.value,25);sameTarget(track,sliderModal,'sliderTrack');
track.onPress();track.onReleaseOutside();assert.equal(p._sliderDragging,false);track.onPress();p.onMouseUp();assert.equal(p._sliderDragging,false);assert.equal(p._modalLayer,sliderModal);
"""
        self.run_js(program)


if __name__ == "__main__":
    unittest.main()
