/**
 * Optional, passive in-game mouse diagnostics. This is not an input fix.
 * The host owns its lifetime: construct on activation and stop on close.
 * Nothing is written to disk, no focus/input state is changed, and no timer
 * or native hook is installed. Missing Scaleform extensions are tolerated.
 */
class MCMCompatMouseProbe
{
	private var _panel:MovieClip;
	private var _overlay:MovieClip;
	private var _output:TextField;
	private var _mouse:Object;
	private var _listening:Boolean;
	private var _stopped:Boolean;
	private var _moves:Number;
	private var _downs:Number;
	private var _ups:Number;
	private var _sideOvers:Number;
	private var _sidePresses:Number;
	private var _lastEvent:String;
	private var _lastIndex:Number;

	public function MCMCompatMouseProbe(panel:MovieClip)
	{
		_panel = panel;
		_listening = false;
		_stopped = false;
		_moves = 0;
		_downs = 0;
		_ups = 0;
		_sideOvers = 0;
		_sidePresses = 0;
		_lastEvent = "none";
		_lastIndex = -1;
		_mouse = _global["Mouse"];
		_createOverlay();
		// Requiring both methods ensures every listener can be removed by stop.
		if (_mouse != undefined && typeof(_mouse.addListener) == "function" &&
			typeof(_mouse.removeListener) == "function") {
			try {
				_listening = _mouse.addListener(this) != false;
			} catch (error:Object) {
				_listening = false;
			}
		}
		_render();
	}

	public function note(event:String, index:Number):Void
	{
		if (!_canObserve())
			return;
		_lastEvent = String(event).substr(0, 40);
		_lastIndex = index;
		if (event == "sideOver" || event == "mods:rollOver" ||
			event == "pages:rollOver") _sideOvers++;
		if (event == "sidePress" || event == "mods:press" ||
			event == "pages:press") _sidePresses++;
		_render();
	}

	public function stop():Void
	{
		if (_stopped)
			return;
		_stopped = true;
		if (_listening && _mouse != undefined &&
			typeof(_mouse.removeListener) == "function") {
			try {
				_mouse.removeListener(this);
			} catch (error:Object) {
				// A stale callback remains inert because _stopped is already set.
			}
		}
		_listening = false;
		if (_overlay != undefined && typeof(_overlay.removeMovieClip) == "function")
			_overlay.removeMovieClip();
		_output = undefined;
		_overlay = undefined;
		_panel = undefined;
		_mouse = undefined;
	}

	public function onMouseMove():Void
	{
		if (!_canObserve())
			return;
		_moves++;
		_render();
	}

	public function onMouseDown():Void
	{
		if (!_canObserve())
			return;
		_downs++;
		_render();
	}

	public function onMouseUp():Void
	{
		if (!_canObserve())
			return;
		_ups++;
		_render();
	}

	private function _canObserve():Boolean
	{
		var visible:Boolean = !_stopped && _panel != undefined &&
			_panel["_active"] == true && _panel._visible == true &&
			(_panel._parent == undefined || _panel._parent._visible == true);
		if (_overlay != undefined)
			_overlay._visible = visible;
		return visible;
	}

	private function _createOverlay():Void
	{
		if (_panel == undefined || typeof(_panel.createEmptyMovieClip) != "function" ||
			typeof(_panel.getNextHighestDepth) != "function")
			return;
		_overlay = _panel.createEmptyMovieClip("_mcmMouseProbeOverlay",
			_panel.getNextHighestDepth());
		if (_overlay == undefined)
			return;
		_overlay._x = 370;
		_overlay._y = 594;
		_overlay["hitTestDisable"] = true;
		// No button/rollover handlers are attached to this clip or its field.
		if (typeof(_overlay.createTextField) != "function")
			return;
		_overlay.createTextField("report", 1, 0, 0, 810, 72);
		_output = _overlay["report"];
		if (_output == undefined)
			return;
		_output["hitTestDisable"] = true;
		_output.selectable = false;
		_output.embedFonts = true;
		_output.type = "dynamic";
		_output.multiline = true;
		_output.wordWrap = false;
		_output.background = true;
		_output.backgroundColor = 0x101010;
		_output.textColor = 0xFFFFFF;
		var format:TextFormat = new TextFormat("$EverywhereFont", 12, 0xFFFFFF);
		format.align = "left";
		format.leading = 0;
		if (typeof(_output.setNewTextFormat) == "function")
			_output.setNewTextFormat(format);
	}

	private function _depth(clip:Object):String
	{
		if (clip == undefined || typeof(clip.getDepth) != "function")
			return "?";
		try {
			return String(clip.getDepth());
		} catch (error:Object) {
			return "?";
		}
	}

	private function _coordinate(value:Object):String
	{
		var number:Number = Number(value);
		return isNaN(number) ? "?" : String(Math.round(number));
	}

	private function _target():String
	{
		if (_mouse == undefined || typeof(_mouse.getTopMostEntity) != "function")
			return "unavailable (no Scaleform hit-test API)";
		try {
			var target:Object = _mouse.getTopMostEntity(false);
			if (target == undefined || target == null)
				return "none";
			var path:String = String(target);
			// Keep the row/leaf name, not a long shared _root/fader prefix.
			if (path.length > 110) path = "..." + path.substr(path.length - 107);
			return path + " @" + _depth(target);
		} catch (error:Object) {
			return "unavailable (hit-test error)";
		}
	}

	private function _render():Void
	{
		if (!_canObserve() || _output == undefined)
			return;
		var journal:Object = _panel["_journal"];
		var journalParent:Object = journal == undefined ? undefined : journal._parent;
		_output.text = "OpenMCM INPUT PROBE (diagnostic)  move=" + _moves +
			" down=" + _downs + " up=" + _ups + "  row=" + _lastEvent +
			" #" + _coordinate(_lastIndex) + "\n" +
			"local x=" + _coordinate(_panel._xmouse) + " y=" + _coordinate(_panel._ymouse) +
			"  state=" + String(_panel["_state"]) + " active=" + String(_panel["_active"]) +
			" listener=" + String(_listening) + " sideOver=" + _sideOvers +
			" sidePress=" + _sidePresses + "\n" +
			"top=" + _target() + "\n" +
			"depth panel=" + _depth(_panel) + " parent=" + _depth(_panel._parent) +
			" side=" + _depth(_panel["_sideRows"]) + " options=" + _depth(_panel["_optionRows"]) +
			" modal=" + _depth(_panel["_modalLayer"]) + " custom=" + _depth(_panel["_customLayer"]) +
			" journal=" + _depth(journal) + " journalParent=" + _depth(journalParent);
	}
}
