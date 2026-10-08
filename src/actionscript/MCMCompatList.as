/**
 * Independent AVM1 list input and renderer lifetime, using SkyUI's public
 * row -> list -> panel event contract without importing its components.
 *
 * The panel supplies layout/paint. This clip owns data, selection and pooled
 * native mouse targets; repainting a row never replaces the button receiving
 * an in-flight mouse event. There are no global mouse/key listeners here.
 */
class MCMCompatList extends MovieClip
{
	public var owner:Object;
	public var kind:String;
	public var entryList:Array;
	public var selectedIndex:Number;
	public var scrollPosition:Number;
	public var visibleCount:Number;
	public var scrollDelta:Number;
	public var disableInput:Boolean;
	public var disableSelection:Boolean;
	public var isListAnimating:Boolean;
	public var isMouseDrivenNav:Boolean;
	public var isAutoUnselect:Boolean;
	public var canSelectDisabled:Boolean;

	// Each callback runs with the panel as its receiver. Events retain the
	// originating list and entry instead of re-reading the panel's active list.
	public var onSelectionChange:Function;
	public var onItemPress:Function;
	public var onRowEvent:Function;
	public var onInput:Function;

	private var _installed:Boolean;
	private var _selectedIndex:Number;
	private var _scrollPosition:Number;
	private var _rows:Array;
	private var _updateEpoch:Number;
	private var _updating:Boolean;
	private var _checkingMouse:Boolean;

	public function MCMCompatList()
	{
		super();
	}

	public static function install(clip:MovieClip, panel:Object, listKind:String):MCMCompatList
	{
		var target:Object = clip;
		target.__proto__ = MCMCompatList.prototype;
		target._initialize(panel, listKind);
		return MCMCompatList(target);
	}

	private function _initialize(panel:Object, listKind:String):Void
	{
		owner = panel;
		kind = listKind;
		if (_installed)
			return;
		_installed = true;
		entryList = [];
		_selectedIndex = -1;
		_scrollPosition = 0;
		visibleCount = 18;
		scrollDelta = 1;
		disableInput = false;
		disableSelection = false;
		isListAnimating = false;
		isMouseDrivenNav = false;
		isAutoUnselect = true;
		canSelectDisabled = false;
		_rows = [];
		_updateEpoch = 0;
		_updating = false;
		_checkingMouse = false;
		focusEnabled = true;
		tabEnabled = false;
		_focusrect = false;
		this.addProperty("selectedIndex", _getSelectedIndex, _setSelectedIndex);
		this.addProperty("scrollPosition", _getScrollPosition, _setScrollPosition);
	}

	private function _getSelectedIndex():Number
	{
		return _selectedIndex;
	}

	private function _setSelectedIndex(index:Number):Void
	{
		selectIndex(index, false);
	}

	private function _getScrollPosition():Number
	{
		return _scrollPosition;
	}

	private function _setScrollPosition(position:Number):Void
	{
		if (isNaN(position))
			return;
		var step:Number = Math.max(1, scrollDelta);
		var maximum:Number = Math.max(0,
			Math.ceil((entryList.length - visibleCount) / step) * step);
		_scrollPosition = Math.max(0, Math.min(maximum, Math.floor(position)));
	}

	/** Programmatic assignments are silent; native input requests notification. */
	public function selectIndex(index:Number, notify:Boolean):Void
	{
		if ((disableSelection && notify) || isNaN(index) || Math.floor(index) != index ||
			index < -1 || index >= entryList.length || index == _selectedIndex)
			return;
		_selectedIndex = index;
		if (notify && onSelectionChange != undefined)
			onSelectionChange.call(owner, _event("selectionChange", index,
				isMouseDrivenNav ? 0 : 1));
	}

	/** Layout transaction: acquire slots in any order, hide unclaimed slots. */
	public function beginUpdate():Void
	{
		_updateEpoch++;
		_updating = true;
	}

	public function getRenderer(slot:Number, index:Number):MovieClip
	{
		if (slot < 0 || Math.floor(slot) != slot)
			return undefined;
		var row:MovieClip = _rows[slot];
		if (row == undefined) {
			row = createEmptyMovieClip("row" + slot, slot + 1);
			_rows[slot] = row;
			row._list = this;
			row._owner = owner;
			row.tabEnabled = false;
			row.focusEnabled = false;
			row.useHandCursor = false;
			row.onRollOver = function():Void {
				this._list.onItemRollOver(this.itemIndex);
			};
			row.onRollOut = function():Void {
				this._list.onItemRollOut(this.itemIndex);
			};
			row.onPress = function(mouseIndex:Number, keyboardOrMouse:Number):Void {
				this._list.pressIndex(this.itemIndex,
					keyboardOrMouse == undefined ? 0 : keyboardOrMouse);
			};
		}
		row._updateEpoch = _updateEpoch;
		row.itemIndex = index;
		row._entryIndex = index;
		row.entry = entryList[index];
		row.isEnabled = true;
		row.enabled = true;
		row._visible = row.entry != undefined;
		return row;
	}

	public function endUpdate():Void
	{
		for (var i:Number = 0; i < _rows.length; i++) {
			var row:MovieClip = _rows[i];
			if (row != undefined && row._updateEpoch != _updateEpoch) {
				row._visible = false;
				row.itemIndex = undefined;
				row._entryIndex = undefined;
				row.entry = undefined;
			}
		}
		_updating = false;
		refreshMouseSelection();
	}

	public function getRendererForIndex(index:Number):MovieClip
	{
		for (var i:Number = 0; i < _rows.length; i++) {
			var row:MovieClip = _rows[i];
			if (row != undefined && row._visible && row._updateEpoch == _updateEpoch &&
				row.itemIndex == index &&
				row.entry == entryList[index])
				return row;
		}
		return undefined;
	}

	/** Rebind hover after scrolling beneath a stationary mouse, as SkyUI does. */
	public function refreshMouseSelection():Void
	{
		if (_updating || _checkingMouse || !isMouseDrivenNav || !_canInteract())
			return;
		_checkingMouse = true;
		var found:Boolean = false;
		for (var i:Number = 0; i < _rows.length; i++) {
			var row:MovieClip = _rows[i];
			if (_validRow(row) && row.hitTest(_root._xmouse, _root._ymouse, true)) {
				found = true;
				selectIndex(row.itemIndex, true);
				break;
			}
		}
		if (!found && isAutoUnselect)
			selectIndex(-1, true);
		_checkingMouse = false;
	}

	public function onItemRollOver(index:Number):Void
	{
		if (!_canInteract() || !_validRow(getRendererForIndex(index)))
			return;
		isMouseDrivenNav = true;
		_traceRow("rollOver", index, 0);
		selectIndex(index, true);
	}

	public function onItemRollOut(index:Number):Void
	{
		if (!_canInteract() || !_validRow(getRendererForIndex(index)))
			return;
		_traceRow("rollOut", index, 0);
		if (isAutoUnselect && index == _selectedIndex) {
			isMouseDrivenNav = true;
			selectIndex(-1, true);
		}
	}

	/** Rollover owns selection; both mouse and keyboard press that selection. */
	public function pressIndex(index:Number, keyboardOrMouse:Number):Void
	{
		if (!_canInteract())
			return;
		if (keyboardOrMouse == undefined)
			keyboardOrMouse = 1;
		// Like SkyUI's BasicListEntry, reject an invalid physical mouse row
		// before asking the list to press its current selection.
		if (index != undefined && !_validRow(getRendererForIndex(index)))
			return;
		if (_selectedIndex < 0 || _selectedIndex >= entryList.length ||
			!_validRow(getRendererForIndex(_selectedIndex)))
			return;
		var pressed:Object = _event("itemPress", _selectedIndex, keyboardOrMouse);
		_traceRow("press", _selectedIndex, keyboardOrMouse);
		if (onItemPress != undefined)
			onItemPress.call(owner, pressed);
	}

	/** The focused component forwards its input once to the panel adapter. */
	public function handleInput(details:Object, pathToFocus:Array):Boolean
	{
		if (disableInput || !_isVisible() || onInput == undefined)
			return false;
		return onInput.call(owner, details, pathToFocus, this) == true;
	}

	private function _event(type:String, index:Number, source:Number):Object
	{
		return {type:type, list:this, kind:kind, index:index,
			entry:entryList[index], clip:getRendererForIndex(index),
			keyboardOrMouse:source};
	}

	private function _traceRow(type:String, index:Number, source:Number):Void
	{
		if (onRowEvent != undefined)
			onRowEvent.call(owner, _event(type, index, source));
	}

	private function _canInteract():Boolean
	{
		return !disableInput && !disableSelection && !isListAnimating && _isVisible();
	}

	private function _validRow(row:MovieClip):Boolean
	{
		return row != undefined && row._visible && row.itemIndex != undefined &&
			row._updateEpoch == _updateEpoch &&
			row.entry != undefined && row.entry == entryList[row.itemIndex] &&
			(row.isEnabled || canSelectDisabled);
	}

	private function _isVisible():Boolean
	{
		var clip:MovieClip = this;
		while (clip != undefined) {
			if (!clip._visible)
				return false;
			clip = clip._parent;
		}
		return true;
	}
}
