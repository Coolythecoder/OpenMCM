/**
 * A code-drawn implementation of the SkyUI MCM ConfigPanel ABI.
 *
 * The class is installed as a prototype mixin on an empty MovieClip.  That
 * lets a vanilla Quest Journal create `_root.ConfigPanelFader.configPanel`
 * dynamically, with no imported SkyUI linkage symbols or timeline assets.
 */
class MCMCompatPanel extends MovieClip
{
	// Public SkyUI ABI option type values.
	public static var OPTION_EMPTY:Number = 0;
	public static var OPTION_HEADER:Number = 1;
	public static var OPTION_TEXT:Number = 2;
	public static var OPTION_TOGGLE:Number = 3;
	public static var OPTION_SLIDER:Number = 4;
	public static var OPTION_MENU:Number = 5;
	public static var OPTION_COLOR:Number = 6;
	public static var OPTION_KEYMAP:Number = 7;
	public static var OPTION_INPUT:Number = 8;

	public static var FLAG_DISABLED:Number = 1;
	public static var FLAG_HIDDEN:Number = 2;
	public static var FLAG_WITH_UNMAP:Number = 4;

	private static var READY:Number = 0;
	private static var WAIT_FOR_OPTION_DATA:Number = 1;
	private static var WAIT_FOR_SLIDER_DATA:Number = 2;
	private static var WAIT_FOR_MENU_DATA:Number = 3;
	private static var WAIT_FOR_COLOR_DATA:Number = 4;
	private static var WAIT_FOR_INPUT_DATA:Number = 5;
	private static var WAIT_FOR_SELECT:Number = 6;
	private static var WAIT_FOR_DEFAULT:Number = 7;
	private static var DIALOG:Number = 8;

	private static var FOCUS_SIDE:Number = 0;
	private static var FOCUS_OPTIONS:Number = 1;

	// Clean-room recreation of the classic SkyUI 6 MCM stage geometry. These
	// are stage-space values for the journal's native 1280x720 canvas.
	private static var FRAME_X:Number = 82;
	private static var FRAME_Y:Number = 70;
	private static var FRAME_W:Number = 1116;
	private static var FRAME_H:Number = 506;
	private static var DIVIDER_X:Number = 330;

	private static var SIDE_X:Number = 168;
	private static var SIDE_Y:Number = 108;
	// SkyUI's list origin is x=168 and its center divider is x=330. Keep the
	// authored 162-pixel span here; a wider field makes right-aligned names and
	// the selection plate cross the divider.
	private static var SIDE_W:Number = 162;
	private static var SIDE_ROW_H:Number = 24;
	private static var SIDE_VISIBLE_ROWS:Number = 18;
	private static var PAGE_SIDE_Y:Number = 145;
	private static var PAGE_VISIBLE_ROWS:Number = 17;

	private static var OPTIONS_PANEL_X:Number = 345;
	private static var OPTIONS_PANEL_Y:Number = 100;
	private static var OPTIONS_X:Number = 352;
	private static var OPTIONS_Y:Number = 131;
	private static var OPTION_W:Number = 380;
	private static var OPTION_GAP:Number = 40;
	private static var OPTION_ROW_H:Number = 33;
	private static var OPTION_VISIBLE_ROWS:Number = 12;

	private static var INFO_X:Number = 377;
	private static var INFO_Y:Number = 568;
	private static var INFO_W:Number = 688;
	private static var TITLE_CENTER_X:Number = 721;
	private static var WELCOME_CENTER_X:Number = 723;
	private static var WELCOME_CENTER_Y:Number = 287;
	private static var FOOTER_BASE_Y:Number = 670;
	private static var DIALOG_X:Number = 518.5;
	private static var DIALOG_W:Number = 401;
	private static var SLIDER_TRACK_X:Number = 596.31;
	private static var SLIDER_TRACK_W:Number = 247.28;

	// Required public properties read/written through Papyrus UI paths.
	public var selectedKeyCode:Number;
	public var optionCursorIndex:Number;
	// Optional evidence collection; never enabled by ordinary MCM navigation.
	public var mouseDiagnosticsEnabled:Boolean;
	private var _mouseProbe:MCMCompatMouseProbe;
	private var _modList:MCMCompatList;
	private var _pageList:MCMCompatList;
	private var _optionsList:MCMCompatList;
	private var _previousDialogFocus:Object;
	private var _dialogFocusOwned:Boolean;
	private var _renderedDialog:Object;
	private var _menuDialogList:MCMCompatList;
	private var _welcomeLayer:MovieClip;
	private var _browser:MCMCompatBrowser;

	private var _mcmCompatInstalled:Boolean;
	private var _journal:Object;
	private var _platform:Number;
	private var _ps3Switch:Boolean;
	private var _state:Number;
	private var _focus:Number;
	private var _active:Boolean;

	private var _modNames:Array;
	private var _pageNames:Array;
	private var _sideItems:Array;
	private var _sideMode:String;
	private var _sideIndex:Number;
	private var _activePageIndex:Number;
	private var _sideScroll:Number;
	private var _selectedModName:String;
	private var _selectedModRegistryIndex:Number;

	private var _optionEntries:Array;
	private var _optionIndex:Number;
	private var _optionScrollRow:Number;
	private var _optionFlagsBuffer:Array;
	private var _optionTextBuffer:Array;
	private var _optionStrValueBuffer:Array;
	private var _optionNumValueBuffer:Array;

	private var _titleText:String;
	private var _infoText:String;
	private var _dialogTitleText:String;
	private var _sliderDialogFormatString:String;
	private var _menuDialogOptions:Array;
	private var _customContentX:Number;
	private var _customContentY:Number;
	private var _customContent:MovieClip;
	private var _welcomeVisible:Boolean;

	private var _highlightIndex:Number;
	private var _highlightIntervalID:Number;
	private var _modListRequestIntervalID:Number;
	private var _modListRequestAttempts:Number;
	private var _requestPageReset:Boolean;
	private var _currentRemapOption:Number;
	private var _remapMode:Boolean;
	private var _remapDelayID:Number;
	private var _sliderDragging:Boolean;
	private var _contentDimmed:Boolean;
	private var _textInputOwned:Boolean;
	// Opt-in extension lifetime, independent of SkyUI's legacy option buffers.
	private var _openMCMApiEnabled:Boolean;
	private var _openMCMPageToken:Number;
	private var _openMCMPageReady:Boolean;

	private var _chrome:MovieClip;
	private var _frameDecor:MovieClip;
	private var _footerDecor:MovieClip;
	private var _titlePlate:MovieClip;
	private var _infoPlate:MovieClip;
	private var _sideRows:MovieClip;
	private var _optionRows:MovieClip;
	private var _customLayer:MovieClip;
	private var _modalLayer:MovieClip;
	private var _titleField:TextField;
	private var _sideHeadingField:TextField;
	private var _optionsHeadingField:TextField;
	private var _infoField:TextField;
	private var _footerField:TextField;
	private var _footerLeftField:TextField;
	private var _footerRightField:TextField;
	private var _sideScrollField:TextField;
	private var _optionScrollField:TextField;
	private var _inputField:TextField;
	private var _dialog:Object;

	public function MCMCompatPanel()
	{
		super();
	}

	/** Install this class' behaviour on a dynamically-created MovieClip. */
	public static function install(target:MovieClip, journal:Object):MovieClip
	{
		var dynamicTarget:Object = target;
		dynamicTarget.__proto__ = MCMCompatPanel.prototype;
		dynamicTarget._initialize(journal);
		return target;
	}

	private function _initialize(journal:Object):Void
	{
		if (_mcmCompatInstalled) {
			_journal = journal;
			return;
		}

		_mcmCompatInstalled = true;
		_journal = journal;
		focusEnabled = true;
		tabEnabled = false;
		_focusrect = false;
		_platform = 0;
		_ps3Switch = false;
		_state = READY;
		_focus = FOCUS_SIDE;
		_active = false;
		selectedKeyCode = -1;
		optionCursorIndex = -1;
		mouseDiagnosticsEnabled = false;

		_modNames = [];
		_pageNames = [];
		_sideItems = _modNames;
		_sideMode = "mods";
		_sideIndex = -1;
		_activePageIndex = -1;
		_sideScroll = 0;
		_selectedModName = "";
		_selectedModRegistryIndex = -1;

		_optionEntries = [];
		_optionIndex = -1;
		_optionScrollRow = 0;
		_optionFlagsBuffer = [];
		_optionTextBuffer = [];
		_optionStrValueBuffer = [];
		_optionNumValueBuffer = [];

		_titleText = "";
		_infoText = "";
		_dialogTitleText = "";
		_sliderDialogFormatString = "{0}";
		_menuDialogOptions = [];
		_customContentX = 0;
		_customContentY = 0;
		_welcomeVisible = false;
		_highlightIndex = -1;
		_modListRequestIntervalID = 0;
		_modListRequestAttempts = 0;
		_requestPageReset = false;
		_currentRemapOption = -1;
		_remapMode = false;
		_sliderDragging = false;
		_contentDimmed = false;
		_textInputOwned = false;
		// The manager synchronizes its persisted preference after the movie is
		// ready. Until then, optional author extensions must fail closed.
		_openMCMApiEnabled = false;
		_openMCMPageToken = 0;
		_openMCMPageReady = false;

		_buildChrome();
		_browser = new MCMCompatBrowser(this);
		this.addProperty("optionCursor", this._getOptionCursor, null);
		this.addProperty("openMCMApiVersion", this._getOpenMCMApiVersion, null);
		this.addProperty("openMCMApiEnabled", this._getOpenMCMApiEnabled, null);
		this.addProperty("openMCMPageToken", this._getOpenMCMPageToken, null);
		this.addProperty("openMCMProviderID", this._getOpenMCMProviderID, null);
		this.addProperty("openMCMPageIndex", this._getOpenMCMPageIndex, null);
		Mouse.addListener(this);
		if (_global["MCM_COMPAT_RAW_KEYS"] == true)
			Key.addListener(this);
		showWelcomeScreen();
	}

	private function _buildChrome():Void
	{
		if (_chrome != undefined)
			_chrome.removeMovieClip();

		_chrome = createEmptyMovieClip("_mcmCompatChrome", 1000);
		_chrome._owner = this;
		_chrome.handleInput = function(details:Object, path:Array):Boolean {
			return this._owner._dispatchFocusedInput(details, path);
		};
		_frameDecor = _chrome.createEmptyMovieClip("frameDecor", 1);
		// SkyUI's MCM leaves the world/journal visible and floats a translucent
		// black ornamental panel above it. Keep this sparse instead of drawing a
		// full-screen card.
		MCMCompatUtil.drawRect(_frameDecor, FRAME_X, FRAME_Y, FRAME_W,
			FRAME_H, 0x000000, 80, 0x999999, 80);
		MCMCompatUtil.drawLine(_frameDecor, DIVIDER_X, 79,
			DIVIDER_X, 567, 0x999999, 80, 1);
		_drawFrameOrnaments(_frameDecor);

		_titlePlate = _chrome.createEmptyMovieClip("titlePlate", 2);
		_infoPlate = _chrome.createEmptyMovieClip("infoPlate", 3);
		_footerDecor = _chrome.createEmptyMovieClip("footerDecor", 4);
		MCMCompatUtil.drawRect(_footerDecor, 0, 0, 1280, 58,
			0x000000, 60, 0x000000, 0);
		MCMCompatUtil.drawLine(_footerDecor, 0, 0, 1280, 0,
			0xAEB0B0, 60, 1);
		MCMCompatUtil.drawDiamond(_footerDecor, 640, 0, 6, 3,
			0xAEB0B0, 60, 0xAEB0B0, 0);
		_titleField = MCMCompatUtil.makeText(_chrome, "titleField", 5,
			358, 61, 730, 34, 24, 0xFFFFFF, true, "center",
			"$EverywhereMediumFont", 0.8, true);
		MCMCompatUtil.applyDropShadow(_titleField, 2, 2, 1.5, 1);
		_sideHeadingField = MCMCompatUtil.makeText(_chrome, "sideHeadingField", 6,
			20, 112.5, 308, 31.5, 22, 0xFFFFFF, true, "right",
			"$EverywhereMediumFont", 0.8);
		MCMCompatUtil.applyDropShadow(_sideHeadingField, 3, 5, 1.0, 1);
		_optionsHeadingField = MCMCompatUtil.makeText(_chrome, "optionsHeadingField", 7,
			OPTIONS_X, 101, 820, 24, 15, 0xFFFFFF, true, "left",
			"$EverywhereMediumFont", 0.8, true);
		_optionsHeadingField._visible = false;
		_infoField = MCMCompatUtil.makeText(_chrome, "infoField", 8,
			408, 576, 630, 26, 18, 0xFFFFFF,
			false, "center", "$EverywhereFont", 0.2);
		MCMCompatUtil.applyDropShadow(_infoField, 2, 2, 1.5, 3);
		_infoField.multiline = true;
		_infoField.wordWrap = true;
		_infoField["verticalAutoSize"] = "top";
		var infoFormat:TextFormat = _infoField.getNewTextFormat();
		infoFormat.leading = 2;
		_infoField.setNewTextFormat(infoFormat);
		_infoField.setTextFormat(infoFormat);
		_footerField = MCMCompatUtil.makeText(_chrome, "footerField", 9,
			0, 0, 1, 1, 1, 0xFFFFFF, false, "left");
		_footerField._visible = false;
		_footerLeftField = MCMCompatUtil.makeText(_chrome, "footerLeftField", 12,
			30, FOOTER_BASE_Y + 8, 720, 32, 20, 0xEBEBEB, true, "left",
			"$EverywhereMediumFont", 0.8, true);
		MCMCompatUtil.applyDropShadow(_footerLeftField, 2, 2, 1.5, 2);
		_footerRightField = MCMCompatUtil.makeText(_chrome, "footerRightField", 13,
			750, FOOTER_BASE_Y + 8, 500, 32, 20, 0xEBEBEB, true, "right",
			"$EverywhereMediumFont", 0.8, true);
		MCMCompatUtil.applyDropShadow(_footerRightField, 2, 2, 1.5, 2);
		_sideScrollField = MCMCompatUtil.makeText(_chrome, "sideScrollField", 10,
			SIDE_X, 535, SIDE_W - 5, 18, 11, 0xB7B7B7, false, "right");
		_optionScrollField = MCMCompatUtil.makeText(_chrome, "optionScrollField", 11,
			1082, 535, 86, 18, 11, 0xB7B7B7, false, "right");

		_installLists();
		_customLayer = _chrome.createEmptyMovieClip("customLayer", 22);
		_welcomeLayer = _chrome.createEmptyMovieClip("welcomeLayer", 23);
		_modalLayer = _chrome.createEmptyMovieClip("modalLayer", 100);
		_customLayer._visible = false;
		_redrawTitlePlate(300);
		_redrawInfoPlate(32);
		_updateFooterPosition();
		_updateFooter();
	}

	/** Lists own data, selection and scroll state; legacy panel accessors are aliases. */
	private function _installLists():Void
	{
		_modList = MCMCompatList.install(_chrome.createEmptyMovieClip("modList", 20), this, "mods");
		_pageList = MCMCompatList.install(_chrome.createEmptyMovieClip("pageList", 24), this, "pages");
		_optionsList = MCMCompatList.install(_chrome.createEmptyMovieClip("optionRows", 21), this, "options");
		_modList.visibleCount = SIDE_VISIBLE_ROWS;
		_pageList.visibleCount = PAGE_VISIBLE_ROWS;
		_optionsList.visibleCount = OPTION_VISIBLE_ROWS * 2;
		_optionsList.scrollDelta = 2;
		_modList.entryList = _modNames;
		_pageList.entryList = _pageNames;
		_optionsList.entryList = _optionEntries;
		var lists:Array = [_modList, _pageList, _optionsList];
		for (var i:Number = 0; i < lists.length; i++) {
			lists[i].onSelectionChange = this._onListSelectionChange;
			lists[i].onItemPress = this._onListPress;
			lists[i].onRowEvent = this._onListRowEvent;
			lists[i].onInput = this._handleComponentInput;
		}
		_optionRows = _optionsList;
		this.addProperty("_sideRows", this._getSideList, null);
		this.addProperty("_sideItems", this._getSideItems, this._setSideItems);
		this.addProperty("_sideIndex", this._getSideIndex, this._setSideIndex);
		this.addProperty("_sideScroll", this._getSideScroll, this._setSideScroll);
		this.addProperty("_optionEntries", this._getOptionEntries, this._setOptionEntries);
		this.addProperty("_optionIndex", this._getOptionIndex, this._setOptionIndex);
		this.addProperty("_optionScrollRow", this._getOptionScroll, this._setOptionScroll);
	}

	private function _getSideList():MCMCompatList { return _sideMode == "pages" ? _pageList : _modList; }
	private function _getSideItems():Array { return _getSideList().entryList; }
	private function _setSideItems(value:Array):Void { _getSideList().entryList = value; }
	private function _getSideIndex():Number { return _getSideList().selectedIndex; }
	private function _setSideIndex(value:Number):Void { _getSideList().selectIndex(value, false); }
	private function _getSideScroll():Number { return _getSideList().scrollPosition; }
	private function _setSideScroll(value:Number):Void { _getSideList().scrollPosition = value; }
	private function _getOptionEntries():Array { return _optionsList.entryList; }
	private function _setOptionEntries(value:Array):Void { _optionsList.entryList = value; }
	private function _getOptionIndex():Number { return _optionsList.selectedIndex; }
	private function _setOptionIndex(value:Number):Void { _optionsList.selectIndex(value, false); }
	private function _getOptionScroll():Number { return _optionsList.scrollPosition / 2; }
	private function _setOptionScroll(value:Number):Void { _optionsList.scrollPosition = value * 2; }

	private function _syncListInput():Void
	{
		var blocked:Boolean = !_active || _contentDimmed || _remapMode;
		_modList._visible = _sideMode == "mods";
		_pageList._visible = _sideMode == "pages";
		_modList.disableInput = _modList.disableSelection = blocked || !_modList._visible;
		_pageList.disableInput = _pageList.disableSelection = blocked || !_pageList._visible;
		_optionsList.disableInput = _optionsList.disableSelection = blocked || _customContent != undefined;
	}

	private function _onListRowEvent(event:Object):Void
	{
		_noteMouseEvent(event.kind + ":" + event.type, event.index);
	}

	private function _onListSelectionChange(event:Object):Void
	{
		if (event.kind == "mods" && event.index >= 0 && this._browser != undefined)
			this._browser.selected(event.entry);
		if (event.index >= 0) {
			_focus = event.kind == "options" ? FOCUS_OPTIONS : FOCUS_SIDE;
			_focusComponent(event.list);
		}
		if (event.kind == "options") _initHighlight(event.index);
		else if (event.index >= 0) _initHighlight(-1);
		_refreshSideSelection();
		_refreshOptionSelection();
		_updateFooter();
	}

	private function _onListPress(event:Object):Void
	{
		if (!_active || _dialog != null || _remapMode || _state != READY)
			return;
		_noteMouseEvent("itemPress:" + event.kind, event.index);
		if (event.kind == "mods") _selectMod(event.entry);
		else if (event.kind == "pages") _selectPage(event.entry);
		else _selectOption(event.index);
	}

	private function _focusComponent(target:Object):Void
	{
		if (!_active || target == undefined) return;
		var gfxPackage:Object = _global["gfx"];
		if (gfxPackage != undefined && gfxPackage.managers != undefined &&
			gfxPackage.managers.FocusHandler != undefined &&
			gfxPackage.managers.FocusHandler.instance != undefined) {
			var manager:Object = gfxPackage.managers.FocusHandler.instance;
			if (manager.getFocus(0) != target) manager.setFocus(target, 0);
		} else if (Selection.getFocus() != String(target)) {
			// Plain AVM1 has no Scaleform focus-rollover suppression. Avoid an
			// unnecessary same-target assignment in the standalone fallback.
			Selection.setFocus(target);
		}
	}

	private function _focusActiveList():Void
	{
		if (_dialog == null && !_remapMode)
			_focusComponent(_focus == FOCUS_OPTIONS ? _optionsList : _getSideList());
	}

	private function _drawFrameOrnaments(clip:MovieClip):Void
	{
		var pale:Number = 0xC5C5C5;
		// Angular flourishes evoke the journal's Nordic filigree while remaining
		// original vector work; no SkyUI shapes or textures are embedded.
		_drawCornerOrnament(clip, FRAME_X, FRAME_Y, 1, 1, pale);
		_drawCornerOrnament(clip, FRAME_X + FRAME_W, FRAME_Y, -1, 1, pale);
		_drawCornerOrnament(clip, FRAME_X, FRAME_Y + FRAME_H, 1, -1, pale);
		_drawCornerOrnament(clip, FRAME_X + FRAME_W, FRAME_Y + FRAME_H,
			-1, -1, pale);

		MCMCompatUtil.drawDiamond(clip, DIVIDER_X, FRAME_Y + 13, 5, 7,
			0x000000, 100, pale, 70);
		MCMCompatUtil.drawDiamond(clip, DIVIDER_X,
			FRAME_Y + FRAME_H - 8, 5, 7, 0x000000, 100, pale, 70);
	}

	private function _drawCornerOrnament(clip:MovieClip, x:Number, y:Number,
		directionX:Number, directionY:Number, color:Number):Void
	{
		MCMCompatUtil.drawLine(clip, x, y + directionY * 28,
			x + directionX * 10, y + directionY * 15, color, 68, 1);
		MCMCompatUtil.drawLine(clip, x + directionX * 10,
			y + directionY * 15, x + directionX * 24,
			y + directionY * 15, color, 68, 1);
		MCMCompatUtil.drawLine(clip, x + directionX * 5,
			y + directionY * 24, x + directionX * 18,
			y + directionY * 7, color, 50, 1);
		MCMCompatUtil.drawDiamond(clip, x + directionX * 18,
			y + directionY * 15, 4, 3, 0x000000, 100, color, 60);
	}

	private function _redrawTitlePlate(width:Number):Void
	{
		var plateWidth:Number = Math.max(300, width);
		var left:Number = TITLE_CENTER_X - plateWidth / 2;
		var right:Number = TITLE_CENTER_X + plateWidth / 2;
		_titlePlate.clear();
		MCMCompatUtil.drawPolygon(_titlePlate, [
			{x:right - 16.75, y:61.75}, {x:right, y:75},
			{x:right - 16.75, y:88.25},
			{x:right - 19.70, y:85.90},
			{x:right - 31.70, y:98}, {x:left + 32.35, y:98},
			{x:left + 19.75, y:85.90}, {x:left + 16.75, y:88.25},
			{x:left, y:75}, {x:left + 16.75, y:61.80},
			{x:left + 19.70, y:64.10}, {x:left + 31.70, y:52},
			{x:right - 32.35, y:52}, {x:right - 19.75, y:64.10}
		], 0x000000, 100, 0x999999, 100, 1);
		MCMCompatUtil.drawLine(_titlePlate, left + 42, 56.2,
			right - 42, 56.2, 0x999999, 100, 1);
		MCMCompatUtil.drawLine(_titlePlate, left + 42, 56.25,
			right - 42, 56.25, 0xD0D0D0, 35, 1);
		MCMCompatUtil.drawPolygon(_titlePlate, [
			{x:left + 16.75, y:61.8}, {x:left + 31.7, y:52},
			{x:left + 23.5, y:66}, {x:left, y:75}
		], 0x999999, 42, 0x999999, 0, 1);
		MCMCompatUtil.drawPolygon(_titlePlate, [
			{x:right - 16.75, y:61.8}, {x:right - 31.7, y:52},
			{x:right - 23.5, y:66}, {x:right, y:75}
		], 0x999999, 42, 0x999999, 0, 1);
		// SkyUI keeps the text in a fixed authored 730px rect; only the
		// ornamental plate changes width around it.
	}

	private function _redrawInfoPlate(height:Number):Void
	{
		var plateHeight:Number = Math.max(32, height);
		_infoPlate.clear();
		MCMCompatUtil.drawPolygon(_infoPlate, [
			{x:INFO_X, y:INFO_Y}, {x:INFO_X + INFO_W, y:INFO_Y},
			{x:INFO_X + INFO_W, y:INFO_Y + plateHeight - 18},
			{x:INFO_X + INFO_W - 18, y:INFO_Y + plateHeight},
			{x:INFO_X + 18, y:INFO_Y + plateHeight},
			{x:INFO_X, y:INFO_Y + plateHeight - 18}
		], 0x000000, 80, 0x999999, 80, 1);
		// The text field is a fixed verticalAutoSize="top" authored field;
		// only the plate grows with its measured text height.
	}

	private function _updateFooterPosition():Void
	{
		var footerY:Number = FOOTER_BASE_Y;
		var safe:Object = Stage["safeRect"];
		if (safe != undefined && !isNaN(Number(safe.y)))
			footerY = FOOTER_BASE_Y + Number(safe.y) - 8;
		_footerDecor._y = footerY;
		// SkyUI's mapped buttons sit at bottomBar local y=-30 and their text at
		// local y=2. The authored panel/fader transforms make that footerY + 22
		// in this panel's stage-space coordinate system.
		_footerLeftField._y = footerY + 22;
		_footerRightField._y = footerY + 22;
	}

	// -----------------------------------------------------------------------------------------
	// Public Papyrus / Quest Journal ABI

	public function initExtensions():Void
	{
		// Vanilla's exact-fit mode stretches the 1280x720 journal on ultrawide
		// displays. SkyUI's ConfigPanel switches the stage to showAll so its
		// authored geometry keeps a 16:9 aspect ratio and remains fully visible.
		Stage.scaleMode = "showAll";
		_updateFooterPosition();
		showWelcomeScreen();
		_updateFooter();
	}

	public function setPlatform(platform:Number, ps3Switch:Boolean):Void
	{
		_platform = platform;
		_ps3Switch = ps3Switch == true;
		_updateFooter();
	}

	public function startPage():Void
	{
		_invalidateOpenMCMPage();
		_active = true;
		_visible = true;
		if (_parent != undefined)
			_parent._visible = true;
		_state = READY;
		_focus = FOCUS_SIDE;
		_sideMode = "mods";
		_sideItems = _modNames;
		_sideIndex = _modNames.length > 0 ? 0 : -1;
		_sideScroll = 0;
		_pageNames = [];
		_pageList.entryList = _pageNames;
		_pageList.selectIndex(-1, false);
		_pageList.scrollPosition = 0;
		_activePageIndex = -1;
		_selectedModName = "";
		_selectedModRegistryIndex = -1;
		_optionEntries = [];
		_optionIndex = -1;
		_optionScrollRow = 0;
		_optionFlagsBuffer = [];
		_optionTextBuffer = [];
		_optionStrValueBuffer = [];
		_optionNumValueBuffer = [];
		optionCursorIndex = -1;
		_requestPageReset = false;
		showWelcomeScreen();
		_renderSide();
		_renderOptions();
		_syncListInput();
		_focusActiveList();
		_updateFooter();
		// Request through SkyUI's long-established selection channel. The -1 value
		// is reserved as a list-refresh sentinel, which also works on existing saves
		// whose co-save predates OpenMCM's optional dedicated request event.
		_beginModListRequest();
		setMouseDiagnostics(mouseDiagnosticsEnabled);
	}

	public function endPage():Void
	{
		if (this._browser != undefined) this._browser.save();
		_invalidateOpenMCMPage();
		if (this._mouseProbe != null) this._mouseProbe.stop();
		this._mouseProbe = null;
		_active = false;
		_stopModListRequest();
		_closeDialog(false);
		_visible = false;
		_syncListInput();
	}

	/** Keyboard-accessible from OpenMCM > Status; does not reroute input. */
	public function setMouseDiagnostics(enabled:Boolean):Void
	{
		if (this._mouseProbe != null) this._mouseProbe.stop();
		this._mouseProbe = null;
		mouseDiagnosticsEnabled = enabled;
		if (enabled && _isVisibleAndActive())
			this._mouseProbe = new MCMCompatMouseProbe(this);
	}

	private function _noteMouseEvent(eventName:String, index:Number):Void
	{
		if (this._mouseProbe != null) this._mouseProbe.note(eventName, index);
	}

	private function _beginModListRequest():Void
	{
		_stopModListRequest();
		_modListRequestAttempts = 0;
		_modListRequestIntervalID = setInterval(this, "_requestModList", 250);
		_requestModList();
	}

	private function _requestModList():Void
	{
		if (!_active || _modListRequestAttempts >= 20) {
			_stopModListRequest();
			return;
		}
		_modListRequestAttempts++;
		MCMCompatUtil.sendModEvent("SKICP_modSelected", null, -1);
	}

	private function _stopModListRequest():Void
	{
		clearInterval(_modListRequestIntervalID);
		_modListRequestIntervalID = 0;
	}

	public function unlock(unused:Boolean):Void
	{
		_state = READY;
		if (MCMCompatExtensions.drain(this)) return;
		if (_requestPageReset) {
			_requestPageReset = false;
			_selectActivePage();
		}
	}

	public function setModNames():Void
	{
		// Receipt of even an empty authoritative array acknowledges the request.
		_stopModListRequest();
		var refreshedNames:Array = [];
		for (var i:Number = 0; i < arguments.length; i++) {
			var raw:String = MCMCompatUtil.safeString(arguments[i]);
			if (raw != "") {
				refreshedNames.push({modIndex:i, modName:raw,
					text:MCMCompatUtil.translate(raw), enabled:true});
			}
		}

		refreshedNames.sort(function(left:Object, right:Object):Number {
			var a:String = String(left.text).toLowerCase();
			var b:String = String(right.text).toLowerCase();
			if (a < b) return -1;
			if (a > b) return 1;
			return 0;
		});
		_modNames = refreshedNames;
		if (this._browser != undefined) _modNames = this._browser.receive(refreshedNames);
		// Registration refreshes the owning component even while its sibling
		// page list is on screen. Back navigation must not expose stale data.
		_modList.entryList = _modNames;

		// SkyUI updates its backing mod list without closing the active page
		// sublist. Registration notifications and menu-open retries can arrive
		// after a player has already selected an MCM, so keep that page and its
		// option/custom-content state intact.
		if (_sideMode == "pages")
			return;

		_invalidateOpenMCMPage();
		_optionEntries = [];
		_optionIndex = -1;
		_optionScrollRow = 0;
		_sideMode = "mods";
		_sideItems = _modNames;
		_sideIndex = _modNames.length > 0 ? 0 : -1;
		_activePageIndex = -1;
		_sideScroll = 0;
		_selectedModName = "";
		if (this._browser != undefined) this._browser.restoreScroll();
		showWelcomeScreen();
		_renderSide();
		_updateFooter();
	}

	/** Save-local fallback; native global preferences take precedence if present. */
	public function loadBrowserState(serialized:String):Void
	{
		if (this._browser != undefined) this._browser.loadSavedGame(serialized);
	}

	public function flushBrowserState():Void
	{
		if (this._browser != undefined) this._browser.save();
	}

	public function openMCMRequestPage(provider:Number, page:Number, token:Number,
		destination:Number, name:String):Boolean
	{
		return MCMCompatExtensions.requestPage(this, provider, page, token, destination, name);
	}

	public function openMCMSetOptionsEnabled(provider:Number, page:Number, token:Number,
		enabled:Number, ids:String):Boolean
	{
		return MCMCompatExtensions.setOptionsEnabled(this, provider, page, token, enabled, ids);
	}

	private function _openBrowserInput(action:String, title:String, text:String, name:String):Void
	{
		if (_dialog != null || _state != READY || _sideMode != "mods") return;
		_state = DIALOG;
		_dialog = {kind:"input", title:title, text:text,
			browserAction:action, browserName:name};
		_renderDialog();
	}

	private function _openBrowserTools():Void
	{
		if (_dialog != null || _state != READY || _sideMode != "mods") return;
		if (this._browser != undefined && _modList.selectedIndex >= 0)
			this._browser.selected(_modList.entryList[_modList.selectedIndex]);
		_state = DIALOG;
		_dialog = {kind:"menu", title:"MCM browser actions", browserAction:"tools",
			options:["Search names", "All menus", "Favourites", "Hidden menus", "Cycle sorting",
				"Toggle favourite", "Hide / unhide", "Rename selected", "Set priority", "Clear search"],
			browserActions:["search", "all", "favorites", "hidden", "sort", "favorite", "hide", "rename", "priority", "clear"],
			selectionIndex:0, activeIndex:0, defaultIndex:0, scroll:0};
		_renderDialog();
	}

	public function setPageNames():Void
	{
		// A second publication may arrive after a page is already open. SkyUI's
		// list state keeps its active entry; retain the same raw provider page
		// identity while still leaving an initial publication unselected.
		var previousPageIndex:Number = -1;
		var previousPageName:String = null;
		if (_sideMode == "pages" && _activePageIndex >= 0 &&
			_activePageIndex < _sideItems.length) {
			previousPageIndex = Number(_sideItems[_activePageIndex].pageIndex);
			previousPageName = String(_sideItems[_activePageIndex].pageName);
		}
		_pageNames = [];
		for (var i:Number = 0; i < arguments.length; i++) {
			var raw:String = MCMCompatUtil.safeString(arguments[i]);
			if (raw.toLowerCase() != "none") {
				_pageNames.push({pageIndex:i, pageName:raw,
					text:MCMCompatUtil.translate(raw), enabled:true});
			}
		}

		_sideMode = "pages";
		_sideItems = _pageNames;
		_sideIndex = -1;
		_activePageIndex = -1;
		_sideScroll = 0;
		if (previousPageIndex >= 0) {
			for (var j:Number = 0; j < _pageNames.length; j++) {
				if (Number(_pageNames[j].pageIndex) == previousPageIndex &&
					String(_pageNames[j].pageName) == previousPageName) {
					_activePageIndex = j;
					_sideIndex = j;
					_ensureSideVisible();
					break;
				}
			}
		}
		// Reordering an unchanged page list is harmless; removing/replacing the
		// active raw provider page invalidates all outstanding extension handles.
		if (previousPageIndex >= 0 && _activePageIndex < 0)
			_invalidateOpenMCMPage();
		_renderSide();
		_renderOptions();
		_updateFooter();
	}

	public function setCustomContentParams(x:Number, y:Number):Void
	{
		_customContentX = isNaN(x) ? 0 : x;
		_customContentY = isNaN(y) ? 0 : y;
	}

	public function loadCustomContent(source:String):Void
	{
		// Provider content replaces the startup splash exactly as it does in
		// SkyUI. In particular, unloading a provider image on a blank page must
		// not reveal the OpenMCM welcome mark underneath it.
		_welcomeVisible = false;
		unloadCustomContent();
		_customLayer._visible = true;
		_optionRows._visible = false;
		_customContent = _customLayer.createEmptyMovieClip("customContent", 1);
		// Match SkyUI's public custom-content coordinate space, whose origin is
		// the options panel rather than the first option entry.
		_customContent._x = OPTIONS_PANEL_X + _customContentX;
		_customContent._y = OPTIONS_PANEL_Y + _customContentY;
		if (source != undefined && source != "")
			_customContent.loadMovie(source);
		_syncListInput();
	}

	public function unloadCustomContent():Void
	{
		if (_customContent != undefined)
			_customContent.removeMovieClip();
		_customContent = undefined;
		_customLayer._visible = false;
		_optionRows._visible = true;
		_renderOptions();
	}

	public function setTitleText(text:String):Void
	{
		_titleText = MCMCompatUtil.translate(text).toUpperCase();
		if (_state != WAIT_FOR_OPTION_DATA)
			_applyTitleText();
	}

	public function setInfoText(text:String):Void
	{
		_infoText = MCMCompatUtil.translateNested(text);
		if (_state != WAIT_FOR_OPTION_DATA)
			_applyInfoText();
	}

	public function setOptionFlagsBuffer():Void
	{
		for (var i:Number = 0; i < arguments.length; i++)
			_optionFlagsBuffer[i] = Number(arguments[i]);
	}

	public function setOptionTextBuffer():Void
	{
		for (var i:Number = 0; i < arguments.length; i++)
			_optionTextBuffer[i] = MCMCompatUtil.translateNested(arguments[i]);
	}

	public function setOptionStrValueBuffer():Void
	{
		for (var i:Number = 0; i < arguments.length; i++) {
			var value:String = MCMCompatUtil.safeString(arguments[i]);
			_optionStrValueBuffer[i] = value.toLowerCase() == "none" ? null : value;
		}
	}

	public function setOptionNumValueBuffer():Void
	{
		for (var i:Number = 0; i < arguments.length; i++)
			_optionNumValueBuffer[i] = Number(arguments[i]);
	}

	public function flushOptionBuffers(optionCount:Number):Void
	{
		_invalidateOpenMCMPage();
		_optionEntries = [];
		var count:Number = Math.max(0, Math.min(128, Math.floor(optionCount)));
		for (var i:Number = 0; i < count; i++) {
			var packed:Number = Number(_optionFlagsBuffer[i]);
			if (isNaN(packed))
				packed = 0;
			_optionEntries.push({
				optionType:packed & 0xFF,
				flags:(packed >>> 8) & 0xFF,
				text:MCMCompatUtil.safeString(_optionTextBuffer[i]),
				strValue:_optionStrValueBuffer[i],
				numValue:Number(_optionNumValueBuffer[i])
			});
		}

		if ((_optionEntries.length % 2) != 0)
			_optionEntries.push({optionType:OPTION_EMPTY, flags:0,
				text:"", strValue:null, numValue:0});

		_optionFlagsBuffer = [];
		_optionTextBuffer = [];
		_optionStrValueBuffer = [];
		_optionNumValueBuffer = [];
		_optionIndex = -1;
		_optionScrollRow = 0;
		_highlightIndex = -1;
		clearInterval(_highlightIntervalID);
		_infoText = "";
		_applyTitleText();
		_applyInfoText();
		_renderOptions();
		_updateFooter();
		_publishOpenMCMPage();
	}

	// OpenMCM API v1. These endpoints deliberately do not replace or alter any
	// SkyUI endpoint. String-array transport is accepted, but every numeric
	// identity is checked before mutating a row or the help/status surface.
	private function _getOpenMCMApiVersion():Number
	{
		return _openMCMApiEnabled ? 1 : 0;
	}

	private function _getOpenMCMApiEnabled():Boolean
	{
		return _openMCMApiEnabled;
	}

	public function setOpenMCMAPIEnabled(enabled:Boolean):Void
	{
		var requested:Boolean = enabled == true;
		if (requested == _openMCMApiEnabled) return;
		_openMCMApiEnabled = requested;
		// A changed preference invalidates already queued optional work. Tokens
		// are republished only by a complete page flush, not by toggling back on.
		_invalidateOpenMCMPage();
	}

	private function _invalidateOpenMCMPage():Void
	{
		this["_openMCMNavigation"] = null;
		_openMCMPageReady = false;
		_openMCMPageToken = 0;
	}

	private function _publishOpenMCMPage():Void
	{
		if (!_isVisibleAndActive() || _sideMode != "pages" ||
			_selectedModRegistryIndex < 0)
			return;
		// A global serial also protects against an old callback after this panel
		// is destroyed and recreated in the same movie. Fail closed at exhaustion
		// rather than reusing a token. Papyrus transports signed 32-bit integers.
		var serial:Number = Number(_global["OpenMCM_APIPageSerial"]);
		if (isNaN(serial)) serial = 0;
		if (serial < 0 || serial >= 2147483647 || Math.floor(serial) != serial)
			return;
		serial++;
		_global["OpenMCM_APIPageSerial"] = serial;
		_openMCMPageToken = serial;
		_openMCMPageReady = true;
	}

	private function _getOpenMCMPageToken():Number
	{
		if (!_openMCMPageReady || !_isVisibleAndActive() || _sideMode != "pages")
			return 0;
		return _openMCMPageToken;
	}

	private function _getOpenMCMProviderID():Number
	{
		return _getOpenMCMPageToken() > 0 ? _selectedModRegistryIndex : -1;
	}

	private function _getOpenMCMPageIndex():Number
	{
		if (_getOpenMCMPageToken() <= 0) return -2;
		if (_activePageIndex >= 0 && _activePageIndex < _pageNames.length)
			return Number(_pageNames[_activePageIndex].pageIndex);
		return -1;
	}

	private function _openMCMMatchesPage(provider:Number, page:Number, token:Number):Boolean
	{
		return !isNaN(provider) && !isNaN(page) && !isNaN(token) &&
			Math.floor(provider) == provider && Math.floor(page) == page &&
			Math.floor(token) == token && token > 0 &&
			token == _getOpenMCMPageToken() &&
			provider == _getOpenMCMProviderID() && page == _getOpenMCMPageIndex();
	}

	private function _openMCMOptionIndex(page:Number, fullID:Number):Number
	{
		if (isNaN(fullID) || fullID < 0 || Math.floor(fullID) != fullID ||
			Math.floor(fullID / 256) != page + 1)
			return -1;
		var index:Number = fullID % 256;
		if (index >= 128 || index >= _optionEntries.length ||
			_optionEntries[index] == undefined ||
			_optionEntries[index].optionType == OPTION_EMPTY)
			return -1;
		return index;
	}

	public function openMCMSetOptionLabel(provider:Number, page:Number, token:Number,
		fullID:Number, text:String):Boolean
	{
		if (!_openMCMApiEnabled) return false;
		provider = Number(provider);
		page = Number(page);
		token = Number(token);
		if (!_openMCMMatchesPage(provider, page, token)) return false;
		var index:Number = _openMCMOptionIndex(page, Number(fullID));
		if (index < 0) return false;
		_optionEntries[index].text = MCMCompatUtil.translateNested(text);
		// Repaint existing entries with their existing index/scroll/focus. Do not
		// flush buffers, reset the page, clear highlights or synthesize callbacks.
		_renderOptions();
		return true;
	}

	public function openMCMSetOptionTextValue(provider:Number, page:Number, token:Number,
		fullID:Number, text:String):Boolean
	{
		if (!_openMCMApiEnabled) return false;
		provider = Number(provider);
		page = Number(page);
		token = Number(token);
		if (!_openMCMMatchesPage(provider, page, token)) return false;
		var index:Number = _openMCMOptionIndex(page, Number(fullID));
		if (index < 0 || _optionEntries[index].optionType != OPTION_TEXT) return false;
		_optionEntries[index].strValue = MCMCompatUtil.safeString(text);
		_renderOptions();
		return true;
	}

	public function openMCMSetInfoText(provider:Number, page:Number, token:Number,
		fullID:Number, text:String):Boolean
	{
		if (!_openMCMApiEnabled) return false;
		return _openMCMSetHelp(provider, page, token, fullID, text, true);
	}

	// Internal compatibility bridge, not an opt-in live-status API. Explicit
	// legacy highlight handlers must retain their help text with extensions off.
	public function openMCMSetHighlightText(provider:Number, page:Number, token:Number,
		fullID:Number, text:String):Boolean
	{
		return _openMCMSetHelp(provider, page, token, fullID, text, false);
	}

	private function _openMCMSetHelp(provider:Number, page:Number, token:Number,
		fullID:Number, text:String, allowStatus:Boolean):Boolean
	{
		provider = Number(provider);
		page = Number(page);
		token = Number(token);
		fullID = Number(fullID);
		if (!_openMCMMatchesPage(provider, page, token)) return false;
		if (fullID == -1 && !allowStatus) return false;
		// -1 is an explicit page status. -2 clears help only while no option is
		// highlighted. All other IDs must still own the current highlight, so a
		// delayed tooltip or rollout cannot replace another row's help.
		if (fullID == -2) {
			if (_highlightIndex != -1) return false;
		} else if (fullID != -1) {
			var index:Number = _openMCMOptionIndex(page, fullID);
			if (index < 0 || index != _highlightIndex) return false;
		}
		setInfoText(text);
		// An opt-in page-ready callback runs after the flush but before the
		// manager's unlock. Unlike legacy buffer publication, this is already a
		// validated live page and must paint its status immediately.
		if (_state == WAIT_FOR_OPTION_DATA) _applyInfoText();
		return true;
	}

	private function _getOptionCursor():Object
	{
		if (optionCursorIndex < 0 || optionCursorIndex >= _optionEntries.length)
			return undefined;
		return _optionEntries[optionCursorIndex];
	}

	public function invalidateOptionData():Void
	{
		_renderOptions();
	}

	public function setOptionFlags():Void
	{
		var index:Number = Number(arguments[0]);
		var flags:Number = Number(arguments[1]);
		if (index >= 0 && index < _optionEntries.length)
			_optionEntries[index].flags = flags;
	}

	public function forcePageReset():Void
	{
		// Defer this until unlock instead of synchronously re-entering a page
		// callback from an arbitrary Papyrus call.
		_requestPageReset = true;
	}

	public function setSliderDialogParams(value:Number, defaultValue:Number,
		minimum:Number, maximum:Number, interval:Number):Void
	{
		if (isNaN(minimum)) minimum = 0;
		if (isNaN(maximum)) maximum = 1;
		if (maximum < minimum) {
			var swap:Number = maximum;
			maximum = minimum;
			minimum = swap;
		}
		if (isNaN(interval) || interval <= 0) interval = 1;
		if (isNaN(value)) value = minimum;
		if (isNaN(defaultValue)) defaultValue = value;
		// CLIK Slider clamps first and then snaps against zero, not against the
		// configured minimum. This distinction is observable for fractional
		// ranges whose minimum is not an interval multiple.
		value = _lockSliderValue(value, minimum, maximum, interval);

		_state = DIALOG;
		_dialog = {kind:"slider", title:_dialogTitleText, value:value,
			defaultValue:defaultValue, minimum:minimum, maximum:maximum,
			interval:interval, format:_sliderDialogFormatString};
		_renderDialog();
	}

	public function setMenuDialogOptions():Void
	{
		_menuDialogOptions = [];
		for (var i:Number = 0; i < arguments.length; i++) {
			var value:String = MCMCompatUtil.safeString(arguments[i]);
			if (value == "" || value.toLowerCase() == "none")
				break;
			_menuDialogOptions.push(MCMCompatUtil.translateNested(value));
		}
	}

	public function setMenuDialogParams(startIndex:Number, defaultIndex:Number):Void
	{
		var count:Number = _menuDialogOptions.length;
		if (count == 0)
			startIndex = -1;
		else if (isNaN(startIndex) || startIndex < -1 || startIndex >= count)
			startIndex = -1;
		if (isNaN(defaultIndex) || defaultIndex < -1 || defaultIndex >= count)
			defaultIndex = -1;

		_state = DIALOG;
		var initialScroll:Number = startIndex >= 5 ? startIndex - 4 : 0;
		_dialog = {kind:"menu", title:_dialogTitleText,
			options:_menuDialogOptions.concat(), selectionIndex:startIndex,
			activeIndex:startIndex,
			defaultIndex:defaultIndex, scroll:initialScroll};
		_renderDialog();
	}

	public function setColorDialogParams(currentColor:Number, defaultColor:Number):Void
	{
		if (isNaN(currentColor)) currentColor = 0;
		if (isNaN(defaultColor)) defaultColor = currentColor;
		var palette:Array = _buildColorPalette();
		_state = DIALOG;
		_dialog = {kind:"color", title:_dialogTitleText,
			color:currentColor, defaultColor:defaultColor, palette:palette,
			colorIndex:_exactColorIndex(currentColor, palette)};
		_renderDialog();
	}

	public function setInputDialogParams(initialText:String):Void
	{
		_state = DIALOG;
		_dialog = {kind:"input", title:_dialogTitleText,
			text:MCMCompatUtil.translateNested(initialText)};
		_renderDialog();
	}

	public function showMessageDialog(text:String, acceptLabel:String,
		cancelLabel:String):Void
	{
		if (_state == READY) {
			// A message is valid only while servicing a locked MCM callback.
			// Reject an out-of-band call immediately so its caller cannot hang.
			MCMCompatUtil.sendModEvent("SKICP_messageDialogClosed", null, 0);
			return;
		}
		_dialog = {kind:"message", title:MCMCompatUtil.translate("$Message"),
			text:MCMCompatUtil.unescapeText(MCMCompatUtil.translateNested(text)),
			acceptLabel:MCMCompatUtil.translate(acceptLabel),
			cancelLabel:MCMCompatUtil.translate(cancelLabel)};
		_renderDialog();
	}

	// @SKSE. Called by StartRemapMode when the next key has been captured.
	public function EndRemapMode(keyCode:Number):Void
	{
		selectedKeyCode = keyCode;
		_state = WAIT_FOR_SELECT;
		MCMCompatUtil.sendModEvent("SKICP_keymapChanged", null, _currentRemapOption);
		_remapDelayID = setInterval(this, "_clearRemap", 200);
		_hideRemapPrompt();
	}

	public function handleInput(details:Object, pathToFocus:Array):Boolean
	{
		if (_remapMode)
			return true;
		if (details == undefined)
			return true;
		// Match Scaleform's focus-chain contract before applying panel-level
		// shortcuts. This preserves caret/control navigation in text inputs and
		// in provider-supplied custom content.
		if (pathToFocus != undefined && pathToFocus.length > 0) {
			var focusPath:Array = pathToFocus.slice();
			var focusTarget:Object = focusPath.shift();
			if (focusTarget != undefined && focusTarget != this &&
				focusTarget.handleInput != undefined &&
				focusTarget.handleInput(details, focusPath))
				return true;
		}
		return _processInput(details);
	}

	private function _handleComponentInput(details:Object, pathToFocus:Array, list:Object):Boolean
	{
		if (!_isVisibleAndActive()) return false;
		list.isMouseDrivenNav = false;
		return _processInput(details);
	}

	private function _dispatchFocusedInput(details:Object, path:Array):Boolean
	{
		if (path != undefined) {
			var remaining:Array = path.slice();
			while (remaining.length > 0) {
				var child:Object = remaining.shift();
				if (child != undefined && child != this && child.handleInput != undefined)
					return child.handleInput(details, remaining);
			}
		}
		return _processInput(details);
	}

	private function _processInput(details:Object):Boolean
	{
		if (_remapMode || details == undefined) return true;
		var value:String = String(details.value).toLowerCase();
		var nav:String = String(details.navEquivalent).toLowerCase();
		if (_dialog != null && _dialog.kind == "slider" &&
			(value == "keyup" || value == "released" || value == "up")) {
			if (nav.indexOf("home") != -1) {
				_dialog.value = _lockSliderValue(_dialog.minimum,
					_dialog.minimum, _dialog.maximum, _dialog.interval);
				_refreshSlider();
			} else if (nav.indexOf("end") != -1) {
				_dialog.value = _lockSliderValue(_dialog.maximum,
					_dialog.minimum, _dialog.maximum, _dialog.interval);
				_refreshSlider();
			}
			return true;
		}
		if (value != "keydown" && value != "keyhold" && value != "pressed" && value != "down")
			return true;

		var control:String = String(details.control).toLowerCase();
		if (nav == "undefined") nav = "";
		if (control == "undefined") control = "";
		var previousFocus:Number = _focus;
		_handleNavigation(nav, control, value == "keyhold");
		if (previousFocus != _focus) _focusActiveList();
		return true;
	}

	/** Optional standalone fallback; enabled with _global.MCM_COMPAT_RAW_KEYS. */
	public function onKeyDown():Void
	{
		if (!_isVisibleAndActive() || _remapMode)
			return;
		var code:Number = Key.getCode();
		// Native TextField input owns printable keys/caret movement. The optional
		// standalone fallback must not interpret a typed space as menu Accept.
		if (_dialog != null && _dialog.kind == "input") {
			if (code == Key.ENTER) _acceptDialog();
			else if (code == Key.ESCAPE || code == Key.TAB) _cancelDialog();
			return;
		}
		if (code == Key.UP) _handleNavigation("up", "", false);
		else if (code == Key.DOWN) _handleNavigation("down", "", false);
		else if (code == Key.LEFT) _handleNavigation("left", "", false);
		else if (code == Key.RIGHT) _handleNavigation("right", "", false);
		else if (code == Key.ENTER || code == Key.SPACE) _handleNavigation("enter", "", false);
		else if (code == Key.ESCAPE || code == Key.TAB) _handleNavigation("tab", "", false);
		else if (code == 82) {
			if (_sideMode == "mods" && this._browser != undefined) this._browser.action("tools");
			else _requestDefaults();
		}
		else if (code == Key.DELETEKEY) _requestUnmap();
	}

	public function onMouseWheel(delta:Number, target:Object):Void
	{
		if (!_isVisibleAndActive())
			return;
		if (_dialog != null) {
			var dialogTop:Number = Number(_dialog.boxY);
			if (_dialog.kind == "menu" &&
				_isPointerInside(DIALOG_X + 25, dialogTop + 50,
					DIALOG_W - 50, 120))
				_scrollMenuDialog(delta > 0 ? -2 : 2);
			else if (_dialog.kind == "slider" &&
				_isPointerInside(549.95, 311.3, 340, 44.71))
				_adjustSlider(-delta);
			return;
		}
		var sideStartY:Number = _sideMode == "pages" ? PAGE_SIDE_Y : SIDE_Y;
		var sideRows:Number = _sideMode == "pages" ? PAGE_VISIBLE_ROWS :
			SIDE_VISIBLE_ROWS;
		if (_isPointerInside(FRAME_X + 9, sideStartY,
			DIVIDER_X - FRAME_X - 9, sideRows * SIDE_ROW_H))
			_scrollSideList(delta > 0 ? -2 : 2);
		else if (_customContent == undefined &&
			_isPointerInside(OPTIONS_PANEL_X, OPTIONS_Y,
				FRAME_X + FRAME_W - OPTIONS_PANEL_X,
				OPTION_VISIBLE_ROWS * OPTION_ROW_H))
			_scrollOptionsList(delta > 0 ? -1 : 1);
	}

	private function _isPointerInside(x:Number, y:Number, width:Number,
		height:Number):Boolean
	{
		return this._xmouse >= x && this._xmouse <= x + width &&
			this._ymouse >= y && this._ymouse <= y + height;
	}

	public function onMouseMove():Void
	{
		if (_sliderDragging && _dialog != null && _dialog.kind == "slider")
			_setSliderFromMouse(this);
	}

	public function onMouseUp():Void
	{
		_sliderDragging = false;
	}

	public function onUnload():Void
	{
		_invalidateOpenMCMPage();
		_active = false;
		_syncListInput();
		if (this._mouseProbe != null) this._mouseProbe.stop();
		this._mouseProbe = null;
		clearInterval(_highlightIntervalID);
		clearInterval(_remapDelayID);
		_stopModListRequest();
		Mouse.removeListener(this);
		Key.removeListener(this);
		_setTextInputEnabled(false);
	}

	// -----------------------------------------------------------------------------------------
	// Main panel navigation and event dispatch

	private function _handleNavigation(nav:String, control:String,
		repeated:Boolean):Void
	{
		var compactControl:String = control.split(" ").join("");
		if (_dialog != null) {
			_handleDialogNavigation(nav, compactControl, repeated);
			return;
		}
		// NavigationCode.PAGE_UP/PAGE_DOWN contains the words "up"/"down".
		// SkyUI gives page scrolling precedence over single-row movement.
		if (nav.indexOf("pageup") != -1) {
			_pageFocusedList(-1);
			return;
		}
		if (nav.indexOf("pagedown") != -1) {
			_pageFocusedList(1);
			return;
		}

		if (nav.indexOf("up") != -1) {
			if (_focus == FOCUS_SIDE) _moveSide(-1);
			else _moveOption(-2);
			return;
		}
		if (nav.indexOf("down") != -1) {
			if (_focus == FOCUS_SIDE) _moveSide(1);
			else _moveOption(2);
			return;
		}
		if (nav.indexOf("left") != -1) {
			if (_focus == FOCUS_OPTIONS && (_optionIndex % 2) == 0) {
				if (_sideMode == "pages" && _sideItems.length > 0) {
					_focus = FOCUS_SIDE;
					_initHighlight(-1);
					_renderSide();
					_renderOptions();
				}
			} else if (_focus == FOCUS_OPTIONS) {
				_moveOption(-1);
			}
			_updateFooter();
			return;
		}
		if (nav.indexOf("right") != -1) {
			if (_focus == FOCUS_SIDE && _optionEntries.length > 0 && _customContent == undefined) {
				_focus = FOCUS_OPTIONS;
				if (_optionIndex < 0) _selectFirstOption();
				_renderSide();
				_renderOptions();
			} else if (_focus == FOCUS_OPTIONS && _optionIndex < 0) {
				_moveOption(1);
			} else if (_focus == FOCUS_OPTIONS && (_optionIndex % 2) == 0) {
				_moveOption(1);
			}
			_updateFooter();
			return;
		}

		if (repeated)
			return;

		if (nav.indexOf("enter") != -1 || nav.indexOf("accept") != -1 ||
			control.indexOf("accept") != -1) {
			_activateCurrent();
			return;
		}
		if (nav.indexOf("tab") != -1 || nav.indexOf("escape") != -1 ||
			control.indexOf("cancel") != -1) {
			_goBack();
			return;
		}
		if (compactControl.indexOf("readyweapon") != -1 ||
			compactControl == "xbutton" ||
			compactControl.indexOf("journalxbutton") != -1) {
			if (_sideMode == "mods" && this._browser != undefined) this._browser.action("tools");
			else _requestDefaults();
			return;
		}
		if (compactControl == "ybutton" ||
			compactControl.indexOf("journalybutton") != -1) {
			_requestUnmap();
			return;
		}
	}

	private function _activateCurrent():Void
	{
		// Keyboard/controller activation follows the same selection-owned list
		// event as native mouse input, including all component lifetime gates.
		var list:MCMCompatList = _focus == FOCUS_OPTIONS ?
			_optionsList : _getSideList();
		list.pressIndex(undefined, 1);
	}

	private function _goBack():Void
	{
		if (_dialog != null || _remapMode || _state != READY) return;
		// SkyUI closes the page sublist in one step even when focus currently
		// sits in the options grid.
		if (_sideMode == "pages") {
			_invalidateOpenMCMPage();
			_focus = FOCUS_SIDE;
			_sideMode = "mods";
			_sideItems = _modNames;
			_sideIndex = _findModListIndex(_selectedModRegistryIndex);
			if (_sideIndex < 0 && _modNames.length > 0)
				_sideIndex = 0;
			_activePageIndex = -1;
			_ensureSideVisible();
			_optionEntries = [];
			_optionIndex = -1;
			unloadCustomContent();
			showWelcomeScreen();
			_renderSide();
			_focusActiveList();
			_updateFooter();
			return;
		}

		if (_focus == FOCUS_OPTIONS) {
			_focus = FOCUS_SIDE;
			_initHighlight(-1);
			if (_sideMode == "pages" && _sideItems.length == 0) {
				_sideMode = "mods";
				_sideItems = _modNames;
				_sideIndex = _modNames.length > 0 ? 0 : -1;
			}
			_renderSide();
			_renderOptions();
			_updateFooter();
			return;
		}

		if (_journal != undefined && _journal.ConfigPanelClose != undefined)
			_journal.ConfigPanelClose();
		else if (_parent != undefined)
			_parent._visible = false;
	}

	private function _selectMod(entry:Object):Void
	{
		if (_state != READY || entry == undefined)
			return;
		if (this._browser != undefined) {
			this._browser.selected(entry);
			this._browser.save();
		}

		_invalidateOpenMCMPage();
		_state = WAIT_FOR_OPTION_DATA;
		_selectedModName = entry.text;
		_selectedModRegistryIndex = Number(entry.modIndex);
		_pageNames = [];
		_sideMode = "pages";
		_sideItems = _pageNames;
		_sideIndex = -1;
		_activePageIndex = -1;
		_sideScroll = 0;
		_optionEntries = [];
		_optionIndex = -1;
		_optionScrollRow = 0;
		_welcomeVisible = false;
		unloadCustomContent();
		_renderSide();
		_renderOptions();
		_focusActiveList();

		_state = WAIT_FOR_OPTION_DATA;
		MCMCompatUtil.sendModEvent("SKICP_modSelected", null, entry.modIndex);
	}

	private function _selectPage(entry:Object):Void
	{
		if (_state != READY || entry == undefined)
			return;
		_invalidateOpenMCMPage();
		_activePageIndex = -1;
		for (var i:Number = 0; i < _pageNames.length; i++)
			if (_pageNames[i] == entry) _activePageIndex = i;
		_renderSide();
		_state = WAIT_FOR_OPTION_DATA;
		MCMCompatUtil.sendModEvent("SKICP_pageSelected", entry.pageName,
			entry.pageIndex);
	}

	private function _selectActivePage():Void
	{
		if (_state != READY)
			return;
		_invalidateOpenMCMPage();
		if (_sideMode == "pages" && _activePageIndex >= 0 &&
			_activePageIndex < _sideItems.length) {
			var entry:Object = _sideItems[_activePageIndex];
			_state = WAIT_FOR_OPTION_DATA;
			MCMCompatUtil.sendModEvent("SKICP_pageSelected", entry.pageName,
				entry.pageIndex);
		}
		else {
			_state = WAIT_FOR_OPTION_DATA;
			MCMCompatUtil.sendModEvent("SKICP_pageSelected", "", -1);
		}
	}

	private function _selectOption(index:Number):Void
	{
		if (_state != READY || index < 0 || index >= _optionEntries.length)
			return;
		var entry:Object = _optionEntries[index];
		// ConfigPanel.selectOption blocks DISABLED only. Hidden renderers cannot be
		// clicked, but retaining the raw type here matches keyboard activation.
		if ((entry.flags & FLAG_DISABLED) != 0)
			return;
		switch (entry.optionType) {
			case OPTION_TEXT:
			case OPTION_TOGGLE:
				_state = WAIT_FOR_SELECT;
				MCMCompatUtil.sendModEvent("SKICP_optionSelected", null, index);
				break;
			case OPTION_SLIDER:
				_dialogTitleText = entry.text;
				_sliderDialogFormatString = MCMCompatUtil.safeString(entry.strValue);
				_state = WAIT_FOR_SLIDER_DATA;
				MCMCompatUtil.sendModEvent("SKICP_sliderSelected", null, index);
				break;
			case OPTION_MENU:
				_dialogTitleText = entry.text;
				_state = WAIT_FOR_MENU_DATA;
				MCMCompatUtil.sendModEvent("SKICP_menuSelected", null, index);
				break;
			case OPTION_COLOR:
				_dialogTitleText = entry.text;
				_state = WAIT_FOR_COLOR_DATA;
				MCMCompatUtil.sendModEvent("SKICP_colorSelected", null, index);
				break;
			case OPTION_KEYMAP:
				_startRemap(index);
				break;
			case OPTION_INPUT:
				_dialogTitleText = entry.text;
				_state = WAIT_FOR_INPUT_DATA;
				MCMCompatUtil.sendModEvent("SKICP_inputSelected", null, index);
				break;
		}
	}

	private function _startRemap(index:Number):Void
	{
		if (_remapMode)
			return;
		_currentRemapOption = index;
		_remapMode = true;
		_showRemapPrompt();
		if (!MCMCompatUtil.startRemapMode(this)) {
			_remapMode = false;
			_currentRemapOption = -1;
			_state = READY;
			// Hiding the prompt restores list gates and focus. Release remap
			// ownership first, otherwise that restoration leaves lists disabled.
			_hideRemapPrompt();
		}
	}

	private function _clearRemap():Void
	{
		clearInterval(_remapDelayID);
		_remapMode = false;
		_currentRemapOption = -1;
		_syncListInput();
		_focusActiveList();
	}

	private function _showRemapPrompt():Void
	{
		_modalLayer.removeMovieClip();
		_modalLayer = _chrome.createEmptyMovieClip("modalLayer", 100);
		_setContentDimmed(true);
		_acquireDialogFocus();
		var message:String = MCMCompatUtil.translate(
			"$Press a button to map to this action.");
		var prompt:TextField = MCMCompatUtil.makeText(_modalLayer, "remapPrompt", 2,
			412.4, 307, 617.25, 32.5, 24, 0xFFFFFF, true, "center",
			"$EverywhereMediumFont", 1.0);
		MCMCompatUtil.applyDropShadow(prompt, 2, 2, 1.5, 1);
		MCMCompatUtil.applyText(prompt, message);
		var width:Number = prompt.textWidth + 100;
		var x:Number = 719 - width / 2;
		MCMCompatUtil.drawPolygon(_modalLayer, [
			{x:x + 15, y:290}, {x:x + width - 15, y:290},
			{x:x + width, y:320.825}, {x:x + width - 15, y:351.65},
			{x:x + 15, y:351.65}, {x:x, y:320.825}
		], 0x000000, 100, 0x999999, 100, 1);
	}

	private function _hideRemapPrompt():Void
	{
		_modalLayer.removeMovieClip();
		_modalLayer = _chrome.createEmptyMovieClip("modalLayer", 100);
		_setContentDimmed(false);
		_restoreDialogFocus();
	}

	private function _requestDefaults():Void
	{
		if (_state != READY || _focus != FOCUS_OPTIONS || _optionIndex < 0 ||
			_optionIndex >= _optionEntries.length ||
			(_optionEntries[_optionIndex].flags & FLAG_DISABLED) != 0)
			return;
		_state = WAIT_FOR_DEFAULT;
		MCMCompatUtil.sendModEvent("SKICP_optionDefaulted", null, _optionIndex);
	}

	private function _requestUnmap():Void
	{
		if (_state != READY || _focus != FOCUS_OPTIONS || _optionIndex < 0 ||
			_optionIndex >= _optionEntries.length)
			return;
		var entry:Object = _optionEntries[_optionIndex];
		if ((entry.flags & (FLAG_DISABLED | FLAG_HIDDEN)) != 0 ||
			entry.optionType != OPTION_KEYMAP ||
			!(entry.flags & FLAG_WITH_UNMAP))
			return;
		selectedKeyCode = -1;
		_state = WAIT_FOR_SELECT;
		MCMCompatUtil.sendModEvent("SKICP_keymapChanged", null, _optionIndex);
	}

	private function _initHighlight(index:Number):Void
	{
		if (_state != READY || index == _highlightIndex)
			return;
		_highlightIndex = index;
		clearInterval(_highlightIntervalID);
		_highlightIntervalID = setInterval(this, "_doHighlight", 200, index);
	}

	private function _doHighlight(index:Number):Void
	{
		clearInterval(_highlightIntervalID);
		MCMCompatUtil.sendModEvent("SKICP_optionHighlighted", null, index);
	}

	private function _isOptionSelectable(index:Number):Boolean
	{
		if (index < 0 || index >= _optionEntries.length)
			return false;
		var entry:Object = _optionEntries[index];
		if ((entry.flags & (FLAG_DISABLED | FLAG_HIDDEN)) != 0)
			return false;
		return entry.optionType >= OPTION_TEXT && entry.optionType <= OPTION_INPUT;
	}

	private function _selectFirstOption():Void
	{
		if (_optionEntries.length > 0)
			_setOptionSelection(0);
		else
			_optionIndex = -1;
	}

	private function _pageFocusedList(direction:Number):Void
	{
		if (_focus == FOCUS_SIDE) {
			var visibleRows:Number = _sideMode == "pages" ? PAGE_VISIBLE_ROWS :
				SIDE_VISIBLE_ROWS;
			var maximum:Number = Math.max(0, _sideItems.length - visibleRows);
			_sideScroll = Math.max(0, Math.min(maximum,
				_sideScroll + direction * visibleRows));
			_sideIndex = -1;
			_renderSide();
		} else {
			var totalRows:Number = Math.ceil(_optionEntries.length / 2);
			var maximumRows:Number = Math.max(0,
				totalRows - OPTION_VISIBLE_ROWS);
			_optionScrollRow = Math.max(0, Math.min(maximumRows,
				_optionScrollRow + direction * OPTION_VISIBLE_ROWS));
			_optionIndex = -1;
			_renderOptions();
			_initHighlight(-1);
		}
		_updateFooter();
	}

	private function _scrollSideList(direction:Number):Void
	{
		if (_getSideList().disableInput) return;
		_getSideList().isMouseDrivenNav = true;
		var visibleRows:Number = _sideMode == "pages" ? PAGE_VISIBLE_ROWS :
			SIDE_VISIBLE_ROWS;
		var maximum:Number = Math.max(0, _sideItems.length - visibleRows);
		var scroll:Number = Math.max(0,
			Math.min(maximum, _sideScroll + direction));
		if (scroll == _sideScroll)
			return;
		_sideScroll = scroll;
		_renderSide();
	}

	private function _scrollOptionsList(direction:Number):Void
	{
		if (_optionsList.disableInput) return;
		_optionsList.isMouseDrivenNav = true;
		var totalRows:Number = Math.ceil(_optionEntries.length / 2);
		var maximum:Number = Math.max(0, totalRows - OPTION_VISIBLE_ROWS);
		var scroll:Number = Math.max(0,
			Math.min(maximum, _optionScrollRow + direction));
		if (scroll == _optionScrollRow)
			return;
		_optionScrollRow = scroll;
		_renderOptions();
	}

	private function _moveSide(delta:Number):Void
	{
		if (_sideItems.length == 0)
			return;
		var visibleRows:Number = _sideMode == "pages" ? PAGE_VISIBLE_ROWS :
			SIDE_VISIBLE_ROWS;
		var candidate:Number;
		if (_sideIndex < 0) {
			candidate = delta < 0 ? Math.min(_sideItems.length - 1,
				_sideScroll + visibleRows - 1) : _sideScroll;
		} else {
			candidate = _sideIndex + delta;
			if (candidate < 0 || candidate >= _sideItems.length)
				return;
		}
		_sideIndex = candidate;
		_ensureSideVisible();
		_renderSide();
		_updateFooter();
	}

	private function _setSideSelection(index:Number):Void
	{
		if (_dialog != null || _remapMode || index < 0 ||
			index >= _sideItems.length)
			return;
		_focusPanelForMouse();
		// A rollover must not replace the MovieClip that is about to receive the
		// mouse press. This is also considerably cheaper while the pointer rests
		// on the already-selected entry.
		if (_focus == FOCUS_SIDE && _sideIndex == index)
			return;
		_focus = FOCUS_SIDE;
		_initHighlight(-1);
		_sideIndex = index;
		var previousScroll:Number = _sideScroll;
		_ensureSideVisible();
		if (previousScroll != _sideScroll)
			_renderSide();
		else
			_refreshSideSelection();
		_refreshOptionSelection();
		_updateFooter();
	}

	private function _clearSideMouseSelection(index:Number):Void
	{
		if (_dialog != null || _remapMode || _focus != FOCUS_SIDE ||
			_sideIndex != index)
			return;
		_sideIndex = -1;
		_refreshSideSelection();
		_updateFooter();
	}

	private function _pressSide(index:Number):Void
	{
		if (_dialog != null || _remapMode || index < 0 ||
			index >= _sideItems.length)
			return;
		// Keep activation on the stable panel object. Selecting a different mod
		// changes the list itself after the press has been dispatched.
		_setSideSelection(index);
		_activateCurrent();
	}

	private function _focusPanelForMouse():Void
	{
		_focusActiveList();
	}

	private function _findModListIndex(registryIndex:Number):Number
	{
		for (var i:Number = 0; i < _modNames.length; i++) {
			if (Number(_modNames[i].modIndex) == registryIndex)
				return i;
		}
		return -1;
	}

	private function _moveOption(delta:Number):Void
	{
		if (_optionEntries.length == 0)
			return;
		if (_optionIndex < 0) {
			var firstVisible:Number = _optionScrollRow * 2;
			var lastVisible:Number = Math.min(_optionEntries.length,
				firstVisible + OPTION_VISIBLE_ROWS * 2) - 1;
			_setOptionSelection(delta > 0 && Math.abs(delta) == 2 ?
				firstVisible : lastVisible);
			return;
		}
		var candidate:Number = _optionIndex + delta;
		if (candidate < 0 || candidate >= _optionEntries.length)
			return;
		_setOptionSelection(candidate);
	}

	private function _setOptionSelection(index:Number):Void
	{
		if (_dialog != null || _remapMode || index < 0 ||
			index >= _optionEntries.length)
			return;
		_focusPanelForMouse();
		if (_focus == FOCUS_OPTIONS && _optionIndex == index)
			return;
		_focus = FOCUS_OPTIONS;
		_optionIndex = index;
		var previousScroll:Number = _optionScrollRow;
		_ensureOptionVisible();
		if (previousScroll != _optionScrollRow)
			_renderOptions();
		else
			_refreshOptionSelection();
		_refreshSideSelection();
		_updateFooter();
		_initHighlight(index);
	}

	private function _clearOptionMouseSelection(index:Number):Void
	{
		if (_dialog != null || _remapMode || _focus != FOCUS_OPTIONS ||
			_optionIndex != index)
			return;
		_optionIndex = -1;
		_refreshOptionSelection();
		_updateFooter();
		_initHighlight(-1);
	}

	private function _pressOption(index:Number):Void
	{
		if (_dialog != null || _remapMode || !_isOptionSelectable(index))
			return;
		_setOptionSelection(index);
		_selectOption(index);
	}

	private function _ensureSideVisible():Void
	{
		var visibleRows:Number = _sideMode == "pages" ? PAGE_VISIBLE_ROWS :
			SIDE_VISIBLE_ROWS;
		if (_sideIndex < _sideScroll)
			_sideScroll = _sideIndex;
		if (_sideIndex >= _sideScroll + visibleRows)
			_sideScroll = _sideIndex - visibleRows + 1;
		if (_sideScroll < 0) _sideScroll = 0;
	}

	private function _ensureOptionVisible():Void
	{
		var row:Number = Math.floor(_optionIndex / 2);
		if (row < _optionScrollRow)
			_optionScrollRow = row;
		if (row >= _optionScrollRow + OPTION_VISIBLE_ROWS)
			_optionScrollRow = row - OPTION_VISIBLE_ROWS + 1;
		if (_optionScrollRow < 0) _optionScrollRow = 0;
	}

	// -----------------------------------------------------------------------------------------
	// Code-native rendering

	/**
	 * SkyUI changes selection on its existing list renderers. Replacing a
	 * hovered MovieClip from its rollover/rollout callback invalidates Flash's
	 * mouse target before the following press. Keep clips, fields and hit areas
	 * alive until the actual list data or visible scroll window changes.
	 */
	private function _refreshSideSelection():Void
	{
		var visibleRows:Number = _sideMode == "pages" ? PAGE_VISIBLE_ROWS :
			SIDE_VISIBLE_ROWS;
		var last:Number = Math.min(_sideItems.length, _sideScroll + visibleRows);
		for (var i:Number = _sideScroll; i < last; i++) {
			var row:MovieClip = _getSideList().getRendererForIndex(i);
			if (row != undefined)
				_drawSideRowState(row, i);
		}
	}

	private function _drawSideRowState(row:MovieClip, index:Number):Void
	{
		row.clear();
		var startY:Number = _sideMode == "pages" ? PAGE_SIDE_Y : SIDE_Y;
		var y:Number = startY + (index - _sideScroll) * SIDE_ROW_H;
		if (index == _sideIndex && _focus == FOCUS_SIDE) {
			var selectedLeft:Number = _sideMode == "pages" ?
				SIDE_X + 2 : SIDE_X - 47;
			MCMCompatUtil.drawHorizontalGradientRect(row, selectedLeft, y,
				DIVIDER_X - selectedLeft, SIDE_ROW_H, 0x999999, 0, 50);
		}
		if (_sideMode == "pages" && index == _activePageIndex) {
			var markerLeft:Number = row.label._x - 23.75;
			var markerCenterY:Number = y + SIDE_ROW_H / 2;
			MCMCompatUtil.drawPolygon(row, [
				{x:markerLeft, y:markerCenterY},
				{x:markerLeft + 7.5, y:markerCenterY - 10},
				{x:markerLeft + 18.75, y:markerCenterY},
				{x:markerLeft + 7.5, y:markerCenterY + 10}
			], 0xFFFFFF, 100, 0xFFFFFF, 0, 1);
		}
	}

	private function _refreshOptionSelection():Void
	{
		var first:Number = _optionScrollRow * 2;
		var last:Number = Math.min(_optionEntries.length,
			first + OPTION_VISIBLE_ROWS * 2);
		for (var i:Number = first; i < last; i++) {
			var row:MovieClip = _optionsList.getRendererForIndex(i);
			var entry:Object = _optionEntries[i];
			if (row != undefined && entry != undefined &&
				entry.optionType != OPTION_HEADER)
				_drawOptionRowState(row, entry, i);
		}
	}

	private function _drawOptionRowState(row:MovieClip, entry:Object,
		index:Number):Void
	{
		row.clear();
		var x:Number = OPTIONS_X + (index % 2) * (OPTION_W + OPTION_GAP);
		var y:Number = OPTIONS_Y +
			(Math.floor(index / 2) - _optionScrollRow) * OPTION_ROW_H;
		var selected:Boolean = index == _optionIndex && _focus == FOCUS_OPTIONS;
		if (selected)
			MCMCompatUtil.drawRadialGradientRect(row, x, y,
				OPTION_W, OPTION_ROW_H, 0xFFFFFF, 40, 0, 180);
		row.label._alpha = selected ? 100 : 75;
		if (entry.optionType == OPTION_COLOR)
			MCMCompatUtil.drawRect(row, x + OPTION_W - 23, y + 4, 23, 23,
				entry.numValue & 0xFFFFFF, 100, 0xD5D5D5, 80);
		else
			_drawOptionGlyph(row, entry, x, y, row.value);
	}

	private function _renderSide():Void
	{
		if (this._browser != undefined) this._browser.render();
		if (_sideRows == undefined)
			return;
		_syncListInput();
		var list:MCMCompatList = _getSideList();
		list.beginUpdate();
		_sideRows.clear();
		_sideRows.titleBack._visible = false;
		_sideRows.sideScrollUp._visible = false;
		_sideRows.sideScrollDown._visible = false;

		var heading:String = _sideMode == "pages" ? _selectedModName : "";
		var startY:Number = _sideMode == "pages" ? PAGE_SIDE_Y : SIDE_Y;
		var visibleRows:Number = _sideMode == "pages" ? PAGE_VISIBLE_ROWS :
			SIDE_VISIBLE_ROWS;
		_sideHeadingField._visible = heading != "";
		MCMCompatUtil.applyText(_sideHeadingField, heading);
		if (heading != "") {
			MCMCompatUtil.drawLine(_sideRows, SIDE_X - 1, PAGE_SIDE_Y - 4,
				DIVIDER_X, PAGE_SIDE_Y - 4, 0xBEBEBE, 38, 1);
			MCMCompatUtil.drawDiamond(_sideRows, DIVIDER_X - 3, PAGE_SIDE_Y - 4,
				4, 3, 0xBEBEBE, 60, 0xBEBEBE, 0);
			// SkyUI's animated sub-list title is also its mouse Back target.
			var titleBack:MovieClip = _sideRows["titleBack"];
			if (titleBack == undefined)
				titleBack = _sideRows.createEmptyMovieClip("titleBack", 1000);
			titleBack._visible = true;
			titleBack.clear();
			MCMCompatUtil.drawRect(titleBack, SIDE_X - 47, SIDE_Y,
				DIVIDER_X - SIDE_X + 47, PAGE_SIDE_Y - SIDE_Y - 4,
				0x000000, 0, 0x000000, 0);
			titleBack.useHandCursor = false;
			titleBack._owner = this;
			titleBack.onPress = function():Void {
				this._owner._goBack();
			};
		}

		if (_sideItems.length == 0) {
			// SkyUI leaves an empty list pane blank. Registration diagnostics in
			// this area changed both the authored appearance and the meaning of an
			// intentionally page-less MCM.
			MCMCompatUtil.applyText(_sideScrollField, "");
			list.endUpdate();
			return;
		}

		var last:Number = Math.min(_sideItems.length,
			_sideScroll + visibleRows);
		for (var i:Number = _sideScroll; i < last; i++) {
			var y:Number = startY + (i - _sideScroll) * SIDE_ROW_H;
			var row:MovieClip = list.getRenderer(i - _sideScroll, i);
			row.clear();
			row.enabled = row.isEnabled = true;
			var active:Boolean = _sideMode == "pages" ?
				i == _activePageIndex : i == _sideIndex;
			var selected:Boolean = i == _sideIndex && _focus == FOCUS_SIDE;
			if (selected) {
				var selectedLeft:Number = _sideMode == "pages" ?
					SIDE_X + 2 : SIDE_X - 47;
				MCMCompatUtil.drawHorizontalGradientRect(row, selectedLeft, y,
					DIVIDER_X - selectedLeft, SIDE_ROW_H, 0x999999, 0, 50);
			}
			// Official list entries retain a transparent trigger area spanning the
			// whole left pane. Text alone is too small and leaves blank rows
			// impossible to click.
			var trigger:MovieClip = row["triggerArea"];
			if (trigger == undefined) trigger = row.createEmptyMovieClip("triggerArea", 0);
			trigger.clear();
			MCMCompatUtil.drawRect(trigger, FRAME_X + 9, y,
				DIVIDER_X - FRAME_X - 9, SIDE_ROW_H, 0x000000, 100,
				0x000000, 0);
			trigger._alpha = 0;
			trigger._visible = true;
			row.useHandCursor = false;
			var labelWidth:Number = _sideMode == "pages" ? 155 : 158;
			var labelY:Number = y + (_sideMode == "pages" ? 2 : 2.5);
			var labelHeight:Number = _sideMode == "pages" ? 24 : 27;
			var label:TextField = MCMCompatUtil.makeText(row, "label", 1,
				SIDE_X + 2, labelY, labelWidth, labelHeight,
				_sideMode == "pages" ? 16 : 15, 0xFFFFFF, false, "right",
				"$EverywhereMediumFont", 0.8, true);
			MCMCompatUtil.applyDropShadow(label, 3, 5, 1.0, 1);
			label.autoSize = "right";
			row._alpha = 100;
			MCMCompatUtil.applyText(label, _sideItems[i].text);
			var favoriteMarker:TextField = MCMCompatUtil.makeText(row, "favoriteMarker", 2,
				FRAME_X + 14, labelY, 20, labelHeight, 16, 0xE8D9A0, false, "left",
				"$EverywhereMediumFont", 0.8, true);
			MCMCompatUtil.applyText(favoriteMarker,
				_sideMode == "mods" && _sideItems[i].favorite ? "*" : "");
			if (_sideMode == "pages" && active) {
				var markerLeft:Number = label._x - 23.75;
				var markerCenterY:Number = y + SIDE_ROW_H / 2;
				MCMCompatUtil.drawPolygon(row, [
					{x:markerLeft, y:markerCenterY},
					{x:markerLeft + 7.5, y:markerCenterY - 10},
					{x:markerLeft + 18.75, y:markerCenterY},
					{x:markerLeft + 7.5, y:markerCenterY + 10}
				], 0xFFFFFF, 100, 0xFFFFFF, 0, 1);
			}
		}

		// The authored SkyUI side lists use centered overflow cues rather than a
		// numeric page counter or a right-edge scrollbar.
		MCMCompatUtil.applyText(_sideScrollField, "");
		var maximumScroll:Number = Math.max(0,
			_sideItems.length - visibleRows);
		if (_sideScroll > 0)
			_drawSideScrollCue(_sideRows, 91, -1, "sideScrollUp", 1100);
		if (_sideScroll < maximumScroll)
			_drawSideScrollCue(_sideRows, 555, 1, "sideScrollDown", 1101);
		list.endUpdate();
	}

	private function _drawSideScrollCue(clip:MovieClip, y:Number,
		direction:Number, name:String, depth:Number):Void
	{
		var cue:MovieClip = clip[name];
		if (cue == undefined) cue = clip.createEmptyMovieClip(name, depth);
		cue._visible = true;
		cue.clear();
		var centerX:Number = 216;
		var tipY:Number = y + direction * 8;
		var baseY:Number = y - direction * 8;
		MCMCompatUtil.drawLine(cue, centerX - 19.3, baseY, centerX, tipY,
			0xD2D2D2, 72, 2);
		MCMCompatUtil.drawLine(cue, centerX, tipY, centerX + 19.3, baseY,
			0xD2D2D2, 72, 2);
		var hit:MovieClip = cue["triggerArea"];
		if (hit == undefined) hit = cue.createEmptyMovieClip("triggerArea", 1);
		hit.clear();
		MCMCompatUtil.drawRect(hit, centerX - 20, y - 9, 40, 18,
			0x000000, 0, 0x000000, 0);
		hit._visible = true;
		cue.useHandCursor = false;
		cue._owner = this;
		cue._direction = direction;
		cue.onPress = function():Void {
			this._owner._scrollSideList(this._direction);
		};
	}

	private function _renderOptions():Void
	{
		if (_optionRows == undefined)
			return;
		_syncListInput();
		_optionsList.beginUpdate();
		_optionRows.clear();
		_welcomeLayer._visible = _welcomeVisible && _optionEntries.length == 0 && _customContent == undefined;
		if (_customContent != undefined) {
			_optionRows._visible = false;
			_optionsList.endUpdate();
			return;
		}
		_optionRows._visible = true;
		if (_optionEntries.length == 0) {
			if (_welcomeVisible)
				_renderWelcomeMark(_welcomeLayer);
			MCMCompatUtil.applyText(_optionScrollField, "");
			_optionsList.endUpdate();
			return;
		}
		// This separator belongs to the populated two-column options list. Keeping
		// it out of the permanent frame prevents it crossing the welcome screen or
		// custom-content SWFs.
		MCMCompatUtil.drawLine(_optionRows, 752, 101, 752, 547,
			0x999999, 50, 1);

		var first:Number = _optionScrollRow * 2;
		var last:Number = Math.min(_optionEntries.length,
			first + OPTION_VISIBLE_ROWS * 2);
		for (var i:Number = first; i < last; i++) {
			var entry:Object = _optionEntries[i];
			if (entry == undefined || entry.optionType == OPTION_EMPTY ||
				(entry.flags & FLAG_HIDDEN) != 0)
				continue;

			var column:Number = i % 2;
			var rowIndex:Number = Math.floor(i / 2) - _optionScrollRow;
			var x:Number = OPTIONS_X + column * (OPTION_W + OPTION_GAP);
			var y:Number = OPTIONS_Y + rowIndex * OPTION_ROW_H;
			var row:MovieClip = _optionsList.getRenderer(i - first, i);
			row.clear();
			row.label._visible = false;
			row.value._visible = false;
			row.header._visible = false;
			row.triggerArea._visible = false;
			var selected:Boolean = i == _optionIndex && _focus == FOCUS_OPTIONS;
			var disabled:Boolean = (entry.flags & FLAG_DISABLED) != 0;
			row.enabled = row.isEnabled = !disabled && entry.optionType != OPTION_HEADER;
			row._alpha = disabled ? 50 : 100;

			if (entry.optionType == OPTION_HEADER) {
				// Header, label and value must have separate depths: this pooled
				// row can change type without replacing any of its text fields.
				var header:TextField = MCMCompatUtil.makeText(row, "header", 3,
					x + 2, y + 3, OPTION_W, 31.4, 22, 0xFFFFFF, true, "left",
					"$EverywhereMediumFont", 0.8, true);
				MCMCompatUtil.applyDropShadow(header, 3, 5, 1.0, 1);
				MCMCompatUtil.applyHtmlText(header, String(entry.text));
				var headerMetrics:Object = header.getLineMetrics(0);
				var renderedHeaderWidth:Number = header.textWidth;
				if (headerMetrics != undefined &&
					!isNaN(Number(headerMetrics.width)))
					renderedHeaderWidth = Number(headerMetrics.width);
				var ruleStart:Number = Math.min(x + OPTION_W - 12,
					x + renderedHeaderWidth + 10);
				MCMCompatUtil.drawDiamond(row, ruleStart + 7.5, y + 16.425,
					7.5, 7.425, 0x000000, 0, 0xAFAFAF, 70);
				MCMCompatUtil.drawDiamond(row, ruleStart + 7.5, y + 16.425,
					3.2, 4.2, 0xAFAFAF, 58, 0xAFAFAF, 0);
				MCMCompatUtil.drawLine(row, ruleStart + 23, y + 13.95,
					x + OPTION_W, y + 13.95, 0xAFAFAF, 58, 1);
				MCMCompatUtil.drawLine(row, ruleStart + 23, y + 18.9,
					x + OPTION_W, y + 18.9, 0xAFAFAF, 38, 1);
				continue;
			}

			if (selected) {
				MCMCompatUtil.drawRadialGradientRect(row, x, y,
					OPTION_W, OPTION_ROW_H, 0xFFFFFF, 40, 0, 180);
			}
			var label:TextField = MCMCompatUtil.makeText(row, "label", 1,
				x + 12, y + 3, OPTION_W, 30.5, 22, 0xFFFFFF, false, "left",
				"$EverywhereFont");
			var labelFormat:TextFormat = label.getNewTextFormat();
			labelFormat.leading = 2;
			label.setNewTextFormat(labelFormat);
			label.setTextFormat(labelFormat);
			MCMCompatUtil.applyDropShadow(label, 2, 2, 1.5, 1);
			label._alpha = selected ? 100 : 75;
			MCMCompatUtil.applyHtmlText(label, entry.text);

			if (entry.optionType == OPTION_COLOR) {
				MCMCompatUtil.drawRect(row, x + OPTION_W - 23, y + 4, 23, 23,
					entry.numValue & 0xFFFFFF, 100, 0xD5D5D5, 80);
			} else {
				var value:TextField = MCMCompatUtil.makeText(row, "value", 2,
					x + 2, y + 3, OPTION_W, 31.7, 20,
					0xFFFFFF, true, "right", "$EverywhereBoldFont");
				var valueFormat:TextFormat = value.getNewTextFormat();
				valueFormat.leading = 2;
				value.setNewTextFormat(valueFormat);
				value.setTextFormat(valueFormat);
				MCMCompatUtil.applyDropShadow(value, 2, 2, 1.5, 1);
				MCMCompatUtil.applyHtmlText(value, _formatOptionValue(entry));
				_drawOptionGlyph(row, entry, x, y, value);
			}

			if (!disabled) {
				var trigger:MovieClip = row["triggerArea"];
				if (trigger == undefined) trigger = row.createEmptyMovieClip("triggerArea", 0);
				trigger.clear();
				MCMCompatUtil.drawRect(trigger, x - 7, y,
					OPTION_W + 7, OPTION_ROW_H, 0x000000, 100,
					0x000000, 0);
				trigger._alpha = 0;
				trigger._visible = true;
				row.useHandCursor = false;
			}
		}

		var totalRows:Number = Math.ceil(_optionEntries.length / 2);
		var totalPages:Number = Math.ceil(totalRows / OPTION_VISIBLE_ROWS);
		MCMCompatUtil.applyText(_optionScrollField, "");
		if (totalPages > 1)
			_drawScrollIndicator(_optionRows, 1169, OPTIONS_Y - 22,
				OPTIONS_Y + OPTION_VISIBLE_ROWS * OPTION_ROW_H - 2,
				_optionScrollRow, Math.max(1, totalRows - OPTION_VISIBLE_ROWS),
				OPTION_VISIBLE_ROWS / totalRows);
		_optionsList.endUpdate();
	}

	private function _drawOptionGlyph(row:MovieClip, entry:Object, x:Number,
		y:Number, valueField:TextField):Void
	{
		var pale:Number = 0xD2D2D2;
		var rightEdge:Number = x + OPTION_W;
		var metrics:Object = valueField.getLineMetrics(0);
		var textStart:Number = valueField._x + valueField._width -
			valueField.textWidth - 4;
		if (metrics != undefined && !isNaN(Number(metrics.x)))
			textStart = valueField._x + Number(metrics.x);
		if (entry.optionType == OPTION_TOGGLE) {
			var toggleX:Number = rightEdge - 12;
			MCMCompatUtil.drawDiamond(row, toggleX, y + 16, 12, 12,
				0x000000, 35, pale, 90);
			if (entry.numValue) {
				MCMCompatUtil.drawDiamond(row, toggleX, y + 16, 6, 6,
					pale, 92, pale, 0);
				MCMCompatUtil.drawLine(row, toggleX - 10, y + 16,
					toggleX + 10, y + 16,
					pale, 42, 1);
			}
		} else if (entry.optionType == OPTION_SLIDER) {
			var sliderRight:Number = textStart - 3;
			MCMCompatUtil.drawDiamond(row, sliderRight - 11, y + 16,
				11, 8, 0x000000, 0, pale, 72);
			MCMCompatUtil.drawDiamond(row, sliderRight - 11, y + 16,
				4, 7, pale, 90,
				pale, 0);
		} else if (entry.optionType == OPTION_MENU) {
			var menuRight:Number = textStart - 3;
			MCMCompatUtil.drawLine(row, menuRight - 7.075, y + 9,
				menuRight, y + 16.5,
				pale, 85, 1);
			MCMCompatUtil.drawLine(row, menuRight, y + 16.5,
				menuRight - 7.075, y + 24,
				pale, 85, 1);
			MCMCompatUtil.drawLine(row, menuRight - 14.15, y + 9,
				menuRight - 7.075, y + 16.5,
				pale, 38, 1);
			MCMCompatUtil.drawLine(row, menuRight - 7.075, y + 16.5,
				menuRight - 14.15, y + 24,
				pale, 38, 1);
		} else if (entry.optionType == OPTION_INPUT) {
			var inputRight:Number = textStart - 6;
			MCMCompatUtil.drawLine(row, inputRight - 8.9, y + 24,
				inputRight, y + 21,
				pale, 75, 1);
			MCMCompatUtil.drawLine(row, inputRight - 8.9, y + 18,
				inputRight - 0.9, y + 9,
				pale, 88, 2);
			MCMCompatUtil.drawDiamond(row, inputRight - 0.9, y + 8, 1.8, 2,
				pale, 90, pale, 0);
		} else if (entry.optionType == OPTION_KEYMAP) {
			var keyWidth:Number = Math.max(42,
				Math.min(142, valueField.textWidth + 18));
			MCMCompatUtil.drawRect(row, rightEdge - keyWidth, y + 5,
				keyWidth, 23, 0x000000, 28, pale, 52);
		}
	}

	private function _drawScrollIndicator(clip:MovieClip, x:Number,
		top:Number, bottom:Number, position:Number, maximum:Number,
		visibleRatio:Number):Void
	{
		var pale:Number = 0xC4C4C4;
		MCMCompatUtil.drawLine(clip, x, top + 10, x, bottom - 10,
			pale, 38, 1);
		MCMCompatUtil.drawDiamond(clip, x, top + 3, 4, 5,
			pale, 70, pale, 0);
		MCMCompatUtil.drawDiamond(clip, x, bottom - 3, 4, 5,
			pale, 70, pale, 0);
		var trackTop:Number = top + 14;
		var trackHeight:Number = bottom - top - 28;
		var thumbHeight:Number = Math.max(18,
			trackHeight * Math.max(0.08, Math.min(1, visibleRatio)));
		var ratio:Number = maximum <= 0 ? 0 :
			Math.max(0, Math.min(1, position / maximum));
		var thumbY:Number = trackTop + (trackHeight - thumbHeight) * ratio;
		MCMCompatUtil.drawRect(clip, x - 2, thumbY, 4, thumbHeight,
			pale, 78, pale, 0);
	}

	private function _renderWelcomeMark(clip:MovieClip):Void
	{
		clip.clear();
		// SkyUI's 256px splash is centered at stage x=723/y=278. The mark uses
		// centerY-9 for its circles, so these constants reproduce that anchor.
		var centerX:Number = WELCOME_CENTER_X;
		var centerY:Number = WELCOME_CENTER_Y;
		var pale:Number = 0xD0D0D0;
		MCMCompatUtil.drawCircle(clip, centerX, centerY - 9, 73,
			0x000000, 18, pale, 58, 1);
		MCMCompatUtil.drawCircle(clip, centerX, centerY - 9, 61,
			0x000000, 0, pale, 24, 1);
		MCMCompatUtil.drawDiamond(clip, centerX, centerY - 82, 7, 5,
			pale, 70, pale, 0);
		MCMCompatUtil.drawDiamond(clip, centerX, centerY + 64, 7, 5,
			pale, 70, pale, 0);
		MCMCompatUtil.drawDiamond(clip, centerX - 73, centerY - 9, 5, 7,
			pale, 70, pale, 0);
		MCMCompatUtil.drawDiamond(clip, centerX + 73, centerY - 9, 5, 7,
			pale, 70, pale, 0);
		// Original knot-mark: four interlocking angular strokes, drawn entirely
		// in code so the distribution contains no copied logo artwork.
		MCMCompatUtil.drawLine(clip, centerX - 37, centerY - 28,
			centerX - 13, centerY + 14, pale, 72, 3);
		MCMCompatUtil.drawLine(clip, centerX - 13, centerY + 14,
			centerX, centerY - 9, pale, 72, 3);
		MCMCompatUtil.drawLine(clip, centerX, centerY - 9,
			centerX + 13, centerY + 14, pale, 72, 3);
		MCMCompatUtil.drawLine(clip, centerX + 13, centerY + 14,
			centerX + 37, centerY - 28, pale, 72, 3);
		MCMCompatUtil.drawLine(clip, centerX - 31, centerY + 19,
			centerX + 31, centerY + 19, pale, 42, 1);

		var monogram:TextField = MCMCompatUtil.makeText(clip, "welcomeMonogram",
			500, centerX - 90, centerY + 75, 180, 48, 42, 0xFFFFFF,
			true, "center", "$EverywhereMediumFont");
		MCMCompatUtil.applyText(monogram, "MCM");
		var label:TextField = MCMCompatUtil.makeText(clip, "welcomeLabel", 501,
			centerX - 220, centerY + 121, 440, 29, 20, 0xFFFFFF,
			true, "center", "$EverywhereMediumFont");
		MCMCompatUtil.applyText(label, "MOD CONFIGURATION MENU");
		var api:TextField = MCMCompatUtil.makeText(clip, "welcomeApi", 502,
			centerX - 160, centerY + 153, 320, 24, 14, 0xBEBEBE,
			false, "center", "$EverywhereFont");
		MCMCompatUtil.applyText(api, "OPENMCM  /  API VERSION 4");
	}

	private function _optionActionLabel(entry:Object):String
	{
		if (entry == undefined)
			return MCMCompatUtil.translate("$Select").toUpperCase();
		switch (entry.optionType) {
			case OPTION_TOGGLE: return MCMCompatUtil.translate("$Toggle").toUpperCase();
			case OPTION_SLIDER: return MCMCompatUtil.translate("$Open Slider").toUpperCase();
			case OPTION_MENU: return MCMCompatUtil.translate("$Open Menu").toUpperCase();
			case OPTION_COLOR: return MCMCompatUtil.translate("$Pick Color").toUpperCase();
			case OPTION_KEYMAP: return MCMCompatUtil.translate("$Remap").toUpperCase();
			case OPTION_INPUT: return MCMCompatUtil.translate("$Input Text").toUpperCase();
		}
		return MCMCompatUtil.translate("$Select").toUpperCase();
	}

	private function _formatOptionValue(entry:Object):String
	{
		switch (entry.optionType) {
			case OPTION_TEXT:
				return MCMCompatUtil.translateNested(entry.strValue).toUpperCase();
			case OPTION_TOGGLE:
				return "";
			case OPTION_SLIDER:
				return MCMCompatUtil.formatSlider(entry.strValue,
					entry.numValue).toUpperCase();
			case OPTION_MENU:
				return MCMCompatUtil.translateNested(entry.strValue).toUpperCase();
			case OPTION_KEYMAP:
				return MCMCompatUtil.keyName(entry.numValue).toUpperCase();
			case OPTION_INPUT:
				return MCMCompatUtil.translateNested(entry.strValue).toUpperCase();
		}
		return "";
	}

	private function _applyTitleText():Void
	{
		MCMCompatUtil.applyText(_titleField, _titleText);
		_redrawTitlePlate(Math.max(300, _titleField.textWidth + 100));
	}

	private function _applyInfoText():Void
	{
		MCMCompatUtil.applyText(_infoField, MCMCompatUtil.unescapeText(_infoText));
		var height:Number = _infoText == "" ? 32 : _infoField.textHeight + 22;
		_redrawInfoPlate(height);
	}

	private function _updateFooter():Void
	{
		_updateFooterPosition();
		_footerLeftField._visible = _dialog == null;
		_footerRightField._visible = _dialog == null;
		var acceptKey:String = _platform == 0 ? "ENTER" : "A";
		var cancelKey:String = _platform == 0 ? "TAB" : "B";
		var defaultKey:String = _platform == 0 ? "R" : "X";
		var unmapKey:String = _platform == 0 ? "T" : "Y";
		if (_platform == 3) {
			acceptKey = _ps3Switch ? "O" : "X";
			cancelKey = _ps3Switch ? "X" : "O";
			defaultKey = "SQUARE";
			unmapKey = "TRIANGLE";
		}
		var selectLabel:String = MCMCompatUtil.translate("$Select").toUpperCase();
		var backLabel:String = MCMCompatUtil.translate("$Back").toUpperCase();
		var exitLabel:String = MCMCompatUtil.translate("$Exit").toUpperCase();
		var defaultLabel:String = MCMCompatUtil.translate("$Default").toUpperCase();
		var unmapLabel:String = MCMCompatUtil.translate("$Unmap").toUpperCase();
		var cancelAction:String = _sideMode == "mods" ? exitLabel : backLabel;
		var left:String = "[ " + acceptKey + " ]  " + selectLabel;
		var right:String = "[ " + cancelKey + " ]  " + cancelAction;

		if (_dialog != null) {
			if (_dialog.kind != "message" && _dialog.kind != "input")
				left = "[ " + defaultKey + " ]  " + defaultLabel;
			right = "[ " + acceptKey + " ]  ACCEPT    [ " + cancelKey +
				" ]  BACK";
		} else if (_focus == FOCUS_SIDE) {
			if (_sideIndex < 0 || _sideIndex >= _sideItems.length)
				left = "";
		} else if (_focus == FOCUS_OPTIONS) {
			right = "[ " + cancelKey + " ]  " + backLabel;
			if (_optionIndex < 0 || _optionIndex >= _optionEntries.length) {
				left = "";
			} else {
				var entry:Object = _optionEntries[_optionIndex];
				if (entry == undefined || entry.optionType == OPTION_EMPTY ||
					entry.optionType == OPTION_HEADER ||
					(entry.flags & (FLAG_DISABLED | FLAG_HIDDEN)) != 0) {
					left = "";
				} else {
					var action:String = _optionActionLabel(entry);
					left = "[ " + acceptKey + " ]  " + action;
					if (entry.optionType == OPTION_KEYMAP &&
						(entry.flags & FLAG_WITH_UNMAP) != 0)
						left += "    [ " + unmapKey + " ]  " + unmapLabel;
					left += "    [ " + defaultKey + " ]  " + defaultLabel;
				}
			}
		}
		MCMCompatUtil.applyTextFit(_footerLeftField, left, 12);
		MCMCompatUtil.applyTextFit(_footerRightField, right, 12);
	}

	public function showWelcomeScreen():Void
	{
		if (_customContent != undefined)
			unloadCustomContent();
		_welcomeVisible = true;
		_titleText = MCMCompatUtil.translate("$MOD CONFIGURATION").toUpperCase();
		_infoText = "";
		_applyTitleText();
		_applyInfoText();
		_renderOptions();
	}

	private function _isVisibleAndActive():Boolean
	{
		return _active && _visible && (_parent == undefined || _parent._visible);
	}

	private function _setContentDimmed(dimmed:Boolean):Void
	{
		if (_contentDimmed != dimmed) {
			MCMCompatBootstrap.playSound(dimmed ?
				"UIMenuBladeOpenSD" : "UIMenuBladeCloseSD");
			_contentDimmed = dimmed;
		}
		var alpha:Number = dimmed ? 75 : 100;
		_frameDecor._alpha = alpha;
		_footerDecor._alpha = alpha;
		_infoPlate._alpha = alpha;
		_sideHeadingField._alpha = alpha;
		_infoField._alpha = alpha;
		_sideRows._alpha = alpha;
		if (this._browser != undefined) this._browser.render();
		_optionRows._alpha = alpha;
		_welcomeLayer._alpha = alpha;
		_customLayer._alpha = alpha;
		_sideScrollField._alpha = alpha;
		_optionScrollField._alpha = alpha;
		_footerLeftField._visible = !dimmed;
		_footerRightField._visible = !dimmed;
		_footerDecor._visible = !dimmed;
		_syncListInput();
	}

	private function _acquireDialogFocus():Void
	{
		if (!_dialogFocusOwned) {
			var gfxPackage:Object = _global["gfx"];
			_previousDialogFocus = _focus == FOCUS_OPTIONS ? _optionsList : _getSideList();
			if (gfxPackage != undefined && gfxPackage.managers != undefined &&
				gfxPackage.managers.FocusHandler != undefined &&
				gfxPackage.managers.FocusHandler.instance != undefined) {
				var previous:Object = gfxPackage.managers.FocusHandler.instance.getFocus(0);
				if (previous != undefined) _previousDialogFocus = previous;
			}
			_dialogFocusOwned = true;
		}
		_modalLayer._owner = this;
		_modalLayer.focusEnabled = true;
		_modalLayer.tabEnabled = false;
		_modalLayer.handleInput = function(details:Object, path:Array):Boolean {
			return this._owner._dispatchFocusedInput(details, path);
		};
		_focusComponent(_modalLayer);
	}

	private function _restoreDialogFocus():Void
	{
		var previous:Object = _previousDialogFocus;
		_previousDialogFocus = undefined;
		_dialogFocusOwned = false;
		if (!_active) return;
		if (previous != undefined && previous._visible != false)
			_focusComponent(previous);
		else _focusActiveList();
	}

	// -----------------------------------------------------------------------------------------
	// Dialog construction and behaviour

	private function _setTextInputEnabled(enabled:Boolean):Void
	{
		// SKSE text input is reference-counted across menus. Release only the
		// request this panel acquired, including repeated close/unload paths.
		if (enabled == _textInputOwned)
			return;
		if (MCMCompatUtil.allowTextInput(enabled))
			_textInputOwned = enabled;
	}

	private function _renderDialog():Void
	{
		if (_dialog == null)
			return;
		_setTextInputEnabled(false);
		// Only a new dialog acquires focus. Scrolling/repainting an existing view
		// must keep the focused control and its native mouse target unchanged.
		if (_renderedDialog != _dialog) {
			_modalLayer.removeMovieClip();
			_modalLayer = _chrome.createEmptyMovieClip("modalLayer", 100);
			_menuDialogList = undefined;
			_renderedDialog = _dialog;
			_acquireDialogFocus();
		}
		_modalLayer.clear();
		_setContentDimmed(true);

		var dialogHeight:Number = 224;
		if (_dialog.kind == "input")
			dialogHeight = 146;
		else if (_dialog.kind == "message") {
			var messageProbe:TextField = MCMCompatUtil.makeText(_modalLayer,
				"messageProbe", 500, -1000, -1000, 330, 2000,
				20, 0xFFFFFF, true, "center", "$EverywhereMediumFont", 1.2);
			messageProbe.multiline = true;
			messageProbe.wordWrap = true;
			var probeFormat:TextFormat = messageProbe.getNewTextFormat();
			probeFormat.leading = 2;
			messageProbe.setNewTextFormat(probeFormat);
			messageProbe.setTextFormat(probeFormat);
			MCMCompatUtil.applyText(messageProbe, _dialog.text);
			dialogHeight = Math.max(75, messageProbe.textHeight) + 78;
			messageProbe.removeTextField();
		}
		var dialogY:Number = 315 - dialogHeight / 2;
		_dialog.boxY = dialogY;
		_dialog.boxHeight = dialogHeight;

		_drawDialogPanel(dialogY, dialogHeight);

		if (_dialog.kind != "message") {
			var titleY:Number = dialogY +
				(_dialog.kind == "input" ? 14 : 12);
			var title:TextField = MCMCompatUtil.makeText(_modalLayer,
				"dialogTitle", 2, DIALOG_X + 27.5, titleY,
				350, 34, 24, 0xFFFFFF, true, "center",
				"$EverywhereMediumFont", 1.2);
			MCMCompatUtil.applyDropShadow(title, 2, 2, 1.5, 2);
			MCMCompatUtil.applyTextFit(title,
				MCMCompatUtil.translateNested(_dialog.title).toUpperCase(), 14);
			var topRuleY:Number = dialogY +
				(_dialog.kind == "input" ? 49.673 : 46.873);
			MCMCompatUtil.drawLine(_modalLayer, DIALOG_X + 13, topRuleY,
				DIALOG_X + 388, topRuleY, 0x999999, 100, 1.75);
			var bottomRuleY:Number = _dialog.kind == "input" ?
				dialogY + 98.373 : dialogY + dialogHeight - 48.5;
			var bottomRuleLeft:Number = _dialog.kind == "input" ?
				DIALOG_X + 13 : DIALOG_X + 12;
			var bottomRuleRight:Number = _dialog.kind == "input" ?
				DIALOG_X + 388 : DIALOG_X + 387;
			MCMCompatUtil.drawLine(_modalLayer, bottomRuleLeft, bottomRuleY,
				bottomRuleRight, bottomRuleY, 0x999999, 100, 1.75);
		}

		switch (_dialog.kind) {
			case "slider": _renderSliderDialog(); break;
			case "menu": _renderMenuDialog(); break;
			case "color": _renderColorDialog(); break;
			case "input": _renderInputDialog(); break;
			case "message": _renderMessageDialog(); break;
		}
		_updateFooter();
	}

	private function _drawDialogPanel(top:Number, height:Number):Void
	{
		var left:Number = DIALOG_X;
		var right:Number = DIALOG_X + DIALOG_W;
		var bottom:Number = top + height;
		// Capped and notched blade silhouette matching SkyUI's dialog footprint,
		// recreated entirely with runtime vectors.
		MCMCompatUtil.drawPolygon(_modalLayer, [
			{x:left + 20.3, y:top}, {x:right - 20.3, y:top},
			{x:right - 20.15, y:top + 3.7}, {x:right, y:top + 3.7},
			{x:right, y:top + 23}, {x:right - 4.3, y:top + 23.3},
			{x:right - 4.3, y:bottom - 23.3},
			{x:right, y:bottom - 23}, {x:right, y:bottom - 3.7},
			{x:right - 20.15, y:bottom - 3.7},
			{x:right - 20.3, y:bottom}, {x:left + 20.3, y:bottom},
			{x:left + 20.15, y:bottom - 3.7}, {x:left, y:bottom - 3.7},
			{x:left, y:bottom - 23}, {x:left + 4.3, y:bottom - 23.3},
			{x:left + 4.3, y:top + 23.3}, {x:left, y:top + 23},
			{x:left, y:top + 3.7}, {x:left + 20.15, y:top + 3.7}
		], 0x000000, 100, 0x999999, 100, 1);
		MCMCompatUtil.drawLine(_modalLayer, left + 20.45, top + 3.7,
			right - 20.55, top + 3.7, 0x999999, 100, 1);
		MCMCompatUtil.drawLine(_modalLayer, left + 20.45, bottom - 3.7,
			right - 20.45, bottom - 3.7, 0x999999, 100, 1);
		MCMCompatUtil.drawLine(_modalLayer, left + 6.1, top + 25,
			left + 6.1, bottom - 25, 0x999999, 100, 2.05);
		MCMCompatUtil.drawLine(_modalLayer, right - 6.1, top + 25,
			right - 6.1, bottom - 25, 0x999999, 100, 2.05);
		_drawDialogCornerBlade(left + 10.5, top + 10.5, 1, 1);
		_drawDialogCornerBlade(right - 10.5, top + 10.5, -1, 1);
		_drawDialogCornerBlade(left + 10.5, bottom - 10.5, 1, -1);
		_drawDialogCornerBlade(right - 10.5, bottom - 10.5, -1, -1);
	}

	private function _drawDialogCornerBlade(x:Number, y:Number,
		directionX:Number, directionY:Number):Void
	{
		MCMCompatUtil.drawLine(_modalLayer, x - directionX * 6,
			y, x + directionX * 6, y, 0x999999, 75, 1);
		MCMCompatUtil.drawLine(_modalLayer, x, y - directionY * 6,
			x, y + directionY * 6, 0x999999, 75, 1);
		MCMCompatUtil.drawLine(_modalLayer, x - directionX * 4,
			y + directionY * 4, x + directionX * 7,
			y - directionY * 7, 0xD0D0D0, 55, 1);
	}

	private function _renderSliderDialog():Void
	{
		var value:TextField = MCMCompatUtil.makeText(_modalLayer, "sliderValue", 3,
			545.5, 282.1, 350, 34.5, 22,
			0xFFFFFF, true, "center", "$EverywhereBoldFont", 0.8, true);
		MCMCompatUtil.applyDropShadow(value, 2, 2, 1.5, 2);
		MCMCompatUtil.applyText(value,
			MCMCompatUtil.formatSlider(_dialog.format, _dialog.value));

		var track:MovieClip = _modalLayer["sliderTrack"];
		if (track == undefined) track = _modalLayer.createEmptyMovieClip("sliderTrack", 4);
		track.clear();
		track.focusEnabled = true;
		track._owner = this;
		track.handleInput = function(details:Object, path:Array):Boolean {
			return this._owner._processInput(details);
		};
		_focusComponent(track);
		var trackY:Number = 333.5;
		MCMCompatUtil.drawRect(track, SLIDER_TRACK_X, 311.3,
			SLIDER_TRACK_W, 44.7, 0x000000, 0, 0x000000, 0);
		MCMCompatUtil.drawLine(track, SLIDER_TRACK_X, trackY,
			SLIDER_TRACK_X + SLIDER_TRACK_W, trackY, 0xBDBDBD, 62, 2);
		var range:Number = _dialog.maximum - _dialog.minimum;
		var ratio:Number = range == 0 ? 0 :
			(_dialog.value - _dialog.minimum) / range;
		MCMCompatUtil.drawLine(track, SLIDER_TRACK_X, trackY,
			SLIDER_TRACK_X + SLIDER_TRACK_W * ratio, trackY,
			0xFFFFFF, 100, 3);
		MCMCompatUtil.drawDiamond(track,
			SLIDER_TRACK_X + SLIDER_TRACK_W * ratio, trackY, 8, 11,
			0xE5E5E5, 100, 0xFFFFFF, 88);
		track._owner = this;
		track.onPress = function():Void {
			this._owner._sliderDragging = true;
			this._owner._setSliderFromMouse(this);
		};
		track.onRelease = function():Void {
			this._owner._sliderDragging = false;
			this._owner._setSliderFromMouse(this);
		};
		track.onReleaseOutside = function():Void {
			this._owner._sliderDragging = false;
		};
		_makeSliderArrow("sliderMinus", 5, 573.12, trackY, -1);
		_makeSliderArrow("sliderPlus", 6, 866.77, trackY, 1);

		_placeLeftButton("sliderDefault", 11, 553, 385,
			MCMCompatUtil.translate("$Default"), "sliderDefault");
		_placeRightButtons("sliderCancel", 12,
			MCMCompatUtil.translate("$Cancel"), "cancel",
			"sliderAccept", 13, MCMCompatUtil.translate("$Accept"), "accept",
			885, 385);
	}

	private function _refreshSlider():Void
	{
		if (_dialog == null || _dialog.kind != "slider")
			return;
		var track:MovieClip = _modalLayer.sliderTrack;
		if (track == undefined)
			return;
		// Live dragging must retain the pressed track and the dialog buttons.
		// Rebuild only the vector drawing and value text, not their MovieClips.
		MCMCompatUtil.applyText(_modalLayer.sliderValue,
			MCMCompatUtil.formatSlider(_dialog.format, _dialog.value));
		track.clear();
		var trackY:Number = 333.5;
		MCMCompatUtil.drawRect(track, SLIDER_TRACK_X, 311.3,
			SLIDER_TRACK_W, 44.7, 0x000000, 0, 0x000000, 0);
		MCMCompatUtil.drawLine(track, SLIDER_TRACK_X, trackY,
			SLIDER_TRACK_X + SLIDER_TRACK_W, trackY, 0xBDBDBD, 62, 2);
		var range:Number = _dialog.maximum - _dialog.minimum;
		var ratio:Number = range == 0 ? 0 :
			(_dialog.value - _dialog.minimum) / range;
		MCMCompatUtil.drawLine(track, SLIDER_TRACK_X, trackY,
			SLIDER_TRACK_X + SLIDER_TRACK_W * ratio, trackY,
			0xFFFFFF, 100, 3);
		MCMCompatUtil.drawDiamond(track,
			SLIDER_TRACK_X + SLIDER_TRACK_W * ratio, trackY, 8, 11,
			0xE5E5E5, 100, 0xFFFFFF, 88);
	}

	private function _makeSliderArrow(name:String, depth:Number,
		centerX:Number, centerY:Number, direction:Number):MovieClip
	{
		var arrow:MovieClip = _modalLayer.createEmptyMovieClip(name, depth);
		MCMCompatUtil.drawPolygon(arrow, [
			{x:centerX + direction * 23.17, y:centerY},
			{x:centerX - direction * 8, y:centerY - 22.35},
			{x:centerX - direction * 23.17, y:centerY - 16},
			{x:centerX - direction * 23.17, y:centerY + 16},
			{x:centerX - direction * 8, y:centerY + 22.35}
		], 0x000000, 35, 0x999999, 80, 1);
		MCMCompatUtil.drawLine(arrow, centerX - direction * 4,
			centerY - 7, centerX + direction * 5, centerY,
			0xD2D2D2, 88, 2);
		MCMCompatUtil.drawLine(arrow, centerX + direction * 5,
			centerY, centerX - direction * 4, centerY + 7,
			0xD2D2D2, 88, 2);
		var hit:MovieClip = arrow.createEmptyMovieClip("hitArea", 1);
		MCMCompatUtil.drawRect(hit, centerX - 23.2, centerY - 22.4,
			46.4, 44.8,
			0x000000, 0, 0x000000, 0);
		arrow.hitArea = hit;
		arrow.useHandCursor = false;
		arrow._owner = this;
		arrow._action = direction < 0 ? "sliderMinus" : "sliderPlus";
		arrow.onPress = function():Void {
			this._owner._dialogAction(this._action);
		};
		return arrow;
	}

	private function _renderMenuDialog():Void
	{
		var options:Array = _dialog.options;
		var visible:Number = 5;
		if (_menuDialogList == undefined) {
			_menuDialogList = MCMCompatList.install(
				_modalLayer.createEmptyMovieClip("menuList", 10), this, "menu");
			_menuDialogList.visibleCount = visible;
			for (var j:Number = 0; j < options.length; j++)
				_menuDialogList.entryList.push({text:options[j], optionIndex:j, enabled:true});
			_menuDialogList.selectIndex(Number(_dialog.selectionIndex), false);
			_menuDialogList.scrollPosition = Number(_dialog.scroll);
			_menuDialogList.onInput = this._handleComponentInput;
			_menuDialogList.onSelectionChange = this._onMenuSelectionChange;
			_menuDialogList.onItemPress = this._onMenuPress;
			_dialog.list = _menuDialogList;
			_dialog.addProperty("selectionIndex", function():Number {
				return this.list.selectedIndex;
			}, function(value:Number):Void { this.list.selectIndex(value, false); });
			_dialog.addProperty("scroll", function():Number {
				return this.list.scrollPosition;
			}, function(value:Number):Void { this.list.scrollPosition = value; });
		}
		_menuDialogList.beginUpdate();
		var last:Number = Math.min(options.length, _dialog.scroll + visible);
		for (var i:Number = _dialog.scroll; i < last; i++) {
			var y:Number = 254 + (i - _dialog.scroll) * 24;
			var row:MovieClip = _menuDialogList.getRenderer(i - _dialog.scroll, i);
			row.clear();
			var selected:Boolean = i == _dialog.selectionIndex;
			var active:Boolean = i == _dialog.activeIndex;
			if (selected)
				MCMCompatUtil.drawCenteredGradientRect(row, 547, y,
					344, 24, 0x999999, 0, 50);
			var label:TextField = MCMCompatUtil.makeText(row, "label", 1,
				549, y + 2, 344, 24, 16,
				0xFFFFFF, selected, "center", "$EverywhereMediumFont", 0.8, true);
			label.autoSize = "center";
			MCMCompatUtil.applyText(label, options[i]);
			if (active) {
				var markerLeft:Number = label._x - 23.75;
				MCMCompatUtil.drawPolygon(row, [
					{x:markerLeft, y:y + 12},
					{x:markerLeft + 7.5, y:y + 2},
					{x:markerLeft + 18.75, y:y + 12},
					{x:markerLeft + 7.5, y:y + 22}
				], 0xFFFFFF, 100, 0xFFFFFF, 0, 1);
			}
			var trigger:MovieClip = row["triggerArea"];
			if (trigger == undefined) trigger = row.createEmptyMovieClip("triggerArea", 0);
			trigger.clear();
			MCMCompatUtil.drawRect(trigger, 547, y,
				344, 24, 0x000000, 100, 0x000000, 0);
			trigger._alpha = 0;
			trigger._visible = true;
			row.useHandCursor = false;
		}
		_menuDialogList.endUpdate();
		_focusComponent(_menuDialogList);
		if (options.length > visible)
			_drawScrollIndicator(_modalLayer, 893, 251,
				376, _dialog.scroll,
				Math.max(1, options.length - visible), visible / options.length);
		_placeLeftButton("menuDefault", 70, 553, 385,
			MCMCompatUtil.translate("$Default"), "menuDefault");
		_placeRightButton("menuAccept", 71, 885, 385,
			MCMCompatUtil.translate("$Exit"), "accept");
	}

	private function _refreshMenuSelection():Void
	{
		var last:Number = Math.min(_dialog.options.length, _dialog.scroll + 5);
		for (var i:Number = _dialog.scroll; i < last; i++) {
			var row:MovieClip = _menuDialogList.getRendererForIndex(i);
			if (row == undefined)
				continue;
			row.clear();
			var y:Number = 254 + (i - _dialog.scroll) * 24;
			if (i == _dialog.selectionIndex)
				MCMCompatUtil.drawCenteredGradientRect(row, 547, y,
					344, 24, 0x999999, 0, 50);
			if (i == _dialog.activeIndex) {
				var markerLeft:Number = row.label._x - 23.75;
				MCMCompatUtil.drawPolygon(row, [
					{x:markerLeft, y:y + 12},
					{x:markerLeft + 7.5, y:y + 2},
					{x:markerLeft + 18.75, y:y + 12},
					{x:markerLeft + 7.5, y:y + 22}
				], 0xFFFFFF, 100, 0xFFFFFF, 0, 1);
			}
		}
	}

	private function _onMenuSelectionChange(event:Object):Void
	{
		if (_dialog == null || _dialog.kind != "menu") return;
		_refreshMenuSelection();
	}

	private function _onMenuPress(event:Object):Void
	{
		if (_dialog == null || _dialog.kind != "menu" || event.entry == undefined) return;
		_dialog.activeIndex = event.entry.optionIndex;
		_refreshMenuSelection();
	}

	private function _renderColorDialog():Void
	{
		var palette:Array = _dialog.palette;
		MCMCompatUtil.drawRect(_modalLayer, 550.5, 290.5, 337, 49,
			0x333333, 100, 0x333333, 0);
		for (var i:Number = 0; i < palette.length; i++) {
			var column:Number = i % 14;
			var line:Number = Math.floor(i / 14);
			var centerX:Number = 563 + column * 24;
			var centerY:Number = 303 + line * 24;
			var selected:Boolean = i == _dialog.colorIndex;
			var size:Number = selected ? 37.5 : 25;
			var swatch:MovieClip = _modalLayer["colorSwatch" + i];
			if (swatch == undefined)
				swatch = _modalLayer.createEmptyMovieClip("colorSwatch" + i, 10 + i);
			if (swatch.getDepth() != 10 + i) swatch.swapDepths(10 + i);
			swatch.clear();
			MCMCompatUtil.drawRect(swatch, centerX - 12.5,
				centerY - 12.5, 25, 25, 0x000000, 0, 0x000000, 0);
			if (selected)
				MCMCompatUtil.drawRect(swatch, centerX - size / 2,
					centerY - size / 2, size, size, 0xFFFFFF, 100,
					0xFFFFFF, 0);
			var pigmentSize:Number = size * 0.7993;
			MCMCompatUtil.drawRect(swatch, centerX - pigmentSize / 2,
				centerY - pigmentSize / 2, pigmentSize, pigmentSize,
				Number(palette[i]), 100, 0xFFFFFF, 0);
			swatch._owner = this;
			swatch._entryIndex = i;
			swatch.focusEnabled = true;
			swatch.handleInput = function(details:Object, path:Array):Boolean {
				return this._owner._processInput(details);
			};
			if (selected) _focusComponent(swatch);
			swatch.onRelease = function():Void {
				this._owner._selectColorIndex(this._entryIndex);
			};
		}
		if (_dialog.colorIndex >= 0)
			_modalLayer["colorSwatch" + _dialog.colorIndex].swapDepths(100);
		_placeLeftButton("colorDefault", 50, 553, 385,
			MCMCompatUtil.translate("$Default"), "colorDefault");
		_placeRightButtons("colorCancel", 51,
			MCMCompatUtil.translate("$Cancel"), "cancel",
			"colorAccept", 52, MCMCompatUtil.translate("$Accept"), "accept",
			885, 385);
	}

	private function _renderInputDialog():Void
	{
		var top:Number = Number(_dialog.boxY);
		MCMCompatUtil.drawRect(_modalLayer, 530.887, top + 50.623,
			376.236, 46.756, 0x141414, 89.84, 0x141414, 89.84);
		_modalLayer.createTextField("inputField", 10, 537.5,
			top + 55, 367, 42);
		_inputField = _modalLayer.inputField;
		_inputField.type = "input";
		_inputField.selectable = true;
		_inputField.embedFonts = true;
		_inputField.multiline = false;
		_inputField.maxChars = _dialog.browserAction == undefined ? 30 : 60;
		if (_dialog.browserAction == "priority") {
			_inputField.maxChars = 3;
			_inputField.restrict = "0-9";
		}
		_inputField.text = MCMCompatUtil.safeString(_dialog.text);
		var format:TextFormat = new TextFormat("$EverywhereMediumFont", 32,
			0xFFFFFF, false, false, false, null, null, "left");
		format.letterSpacing = 0.8;
		format.kerning = false;
		_inputField.setNewTextFormat(format);
		_inputField.setTextFormat(format);
		MCMCompatUtil.applyDropShadow(_inputField, 2, 2, 1.0, 1);
		Selection.setFocus(_inputField);
		_focusComponent(_inputField);
		Selection.setSelection(0, _inputField.text.length);
		_setTextInputEnabled(true);
		_placeRightButtons("inputCancel", 20,
			MCMCompatUtil.translate("$Cancel"), "cancel",
			"inputAccept", 21, MCMCompatUtil.translate("$Accept"), "accept",
			886, top + 104.85);
	}

	private function _renderMessageDialog():Void
	{
		var top:Number = Number(_dialog.boxY);
		var height:Number = Number(_dialog.boxHeight);
		var contentHeight:Number = height - 78;
		var message:TextField = MCMCompatUtil.makeText(_modalLayer, "message", 10,
			556, top + 14, 330, contentHeight,
			20, 0xFFFFFF, true, "center", "$EverywhereMediumFont", 1.2);
		message.multiline = true;
		message.wordWrap = true;
		message["verticalAutoSize"] = "top";
		var messageFormat:TextFormat = message.getNewTextFormat();
		messageFormat.leading = 2;
		message.setNewTextFormat(messageFormat);
		message.setTextFormat(messageFormat);
		MCMCompatUtil.applyDropShadow(message, 2, 2, 1.5, 2);
		MCMCompatUtil.applyText(message, _dialog.text);
		message._y = top + 14 + (contentHeight - message.textHeight) / 2;
		MCMCompatUtil.drawLine(_modalLayer, DIALOG_X + 12,
			top + height - 50, DIALOG_X + 387, top + height - 50,
			0x999999, 100, 1.75);

		var accept:String = _dialog.acceptLabel == "" ?
			MCMCompatUtil.translate("$Accept") : _dialog.acceptLabel;
		if (_dialog.cancelLabel != "") {
			_placeRightButtons("messageCancel", 20,
				_dialog.cancelLabel, "cancel",
				"messageAccept", 21, accept, "accept",
				885, top + height - 42);
		} else {
			_placeRightButton("messageAccept", 21, 885,
				top + height - 42, accept, "accept");
		}
	}

	private function _makeButton(name:String, depth:Number,
		labelText:String, action:String):MovieClip
	{
		var button:MovieClip = _modalLayer[name];
		if (button == undefined) button = _modalLayer.createEmptyMovieClip(name, depth);
		button.clear();
		var label:TextField = MCMCompatUtil.makeText(button, "label", 1,
			0, 2, 150, 27.7, 20, 0xFFFFFF,
			true, "left", "$EverywhereMediumFont", 0.8, true);
		var mappedLabel:String = "[ " + _dialogControlName(action) + " ]  " +
			MCMCompatUtil.safeString(labelText).toUpperCase();
		MCMCompatUtil.applyDropShadow(label, 2, 2, 1.5, 2);
		MCMCompatUtil.applyText(label, mappedLabel);
		label.autoSize = "left";
		button["mappedWidth"] = label.textWidth + 6;
		var hit:MovieClip = button.createEmptyMovieClip("hitArea", 0);
		MCMCompatUtil.drawRect(hit, 0, 0, Number(button["mappedWidth"]), 31,
			0x000000, 0, 0x000000, 0);
		button.hitArea = hit;
		button._owner = this;
		button._action = action;
		button.onRollOver = function():Void { this._alpha = 70; };
		button.onRollOut = function():Void { this._alpha = 100; };
		button.onReleaseOutside = button.onRollOut;
		button.onRelease = function():Void {
			this._alpha = 100;
			this._owner._dialogAction(this._action);
		};
		return button;
	}

	private function _placeLeftButton(name:String, depth:Number, x:Number,
		y:Number, labelText:String, action:String):MovieClip
	{
		var button:MovieClip = _makeButton(name, depth, labelText, action);
		button._x = x;
		button._y = y;
		return button;
	}

	private function _placeRightButton(name:String, depth:Number,
		rightEdge:Number, y:Number, labelText:String, action:String):MovieClip
	{
		var button:MovieClip = _makeButton(name, depth, labelText, action);
		button._x = rightEdge - Number(button["mappedWidth"]);
		button._y = y;
		return button;
	}

	private function _placeRightButtons(cancelName:String, cancelDepth:Number,
		cancelLabel:String, cancelAction:String, acceptName:String,
		acceptDepth:Number, acceptLabel:String, acceptAction:String,
		rightEdge:Number, y:Number):Void
	{
		// SkyUI's right ButtonPanel is reversed. It receives Cancel first, then
		// Accept, so Accept is the left-hand button and Cancel touches the anchor.
		var cancelButton:MovieClip = _placeRightButton(cancelName, cancelDepth,
			rightEdge, y, cancelLabel, cancelAction);
		var acceptButton:MovieClip = _makeButton(acceptName, acceptDepth,
			acceptLabel, acceptAction);
		acceptButton._x = cancelButton._x - 10 -
			Number(acceptButton["mappedWidth"]);
		acceptButton._y = y;
	}

	private function _dialogControlName(action:String):String
	{
		var control:String;
		if (action == "accept")
			control = _platform == 0 ? "ENTER" : "A";
		else if (action == "cancel")
			control = _platform == 0 ? "TAB" : "B";
		else
			control = _platform == 0 ? "R" : "X";
		if (_platform == 3) {
			if (action == "accept") control = _ps3Switch ? "O" : "X";
			else if (action == "cancel") control = _ps3Switch ? "X" : "O";
			else control = "SQUARE";
		}
		return control;
	}

	private function _dialogAction(action:String):Void
	{
		if (_dialog == null)
			return;
		if (action == "accept") _acceptDialog();
		else if (action == "cancel") _cancelDialog();
		else if (action == "sliderMinus") _adjustSlider(-1);
		else if (action == "sliderPlus") _adjustSlider(1);
		else if (action == "sliderDefault") {
			_dialog.value = _lockSliderValue(_dialog.defaultValue,
				_dialog.minimum, _dialog.maximum, _dialog.interval);
			_refreshSlider();
		} else if (action == "menuDefault") {
			_commitMenuDialogSelection(_dialog.defaultIndex);
		} else if (action == "colorDefault") {
			_dialog.color = _dialog.defaultColor;
			_dialog.colorIndex = _exactColorIndex(_dialog.color,
				_dialog.palette);
			_renderDialog();
		}
	}

	private function _handleDialogNavigation(nav:String, compactControl:String,
		repeated:Boolean):Void
	{
		var kind:String = _dialog.kind;
		if (!repeated && (nav.indexOf("tab") != -1 ||
			nav.indexOf("escape") != -1 ||
			compactControl.indexOf("cancel") != -1)) {
			// Classic SkyUI's menu dialog commits its active row when closed.
			if (kind == "menu") _acceptDialog();
			else _cancelDialog();
			return;
		}
		if (!repeated && (nav.indexOf("enter") != -1 ||
			nav.indexOf("accept") != -1 ||
			compactControl.indexOf("accept") != -1)) {
			if (kind == "menu")
				_commitMenuDialogSelection(_dialog.selectionIndex);
			else
				_acceptDialog();
			return;
		}

		if (!repeated && kind != "input" && kind != "message" &&
			(compactControl.indexOf("readyweapon") != -1 ||
			compactControl.indexOf("journalxbutton") != -1 ||
			compactControl == "ybutton")) {
			if (kind == "slider")
				_dialog.value = _lockSliderValue(_dialog.defaultValue,
					_dialog.minimum, _dialog.maximum, _dialog.interval);
			else if (kind == "menu") {
				_commitMenuDialogSelection(_dialog.defaultIndex);
				return;
			}
			else if (kind == "color") {
				_dialog.color = _dialog.defaultColor;
				_dialog.colorIndex = _exactColorIndex(_dialog.color,
					_dialog.palette);
			}
			if (kind == "slider") _refreshSlider();
			else _renderDialog();
			return;
		}

		if (kind == "slider") {
			if (nav.indexOf("pagedown") != -1 ||
				compactControl.indexOf("leftshoulder") != -1)
				_adjustSliderPage(-1);
			else if (nav.indexOf("pageup") != -1 ||
				compactControl.indexOf("rightshoulder") != -1)
				_adjustSliderPage(1);
			else if (nav.indexOf("left") != -1)
				_adjustSlider(-1);
			else if (nav.indexOf("right") != -1)
				_adjustSlider(1);
		} else if (kind == "menu") {
			if (nav.indexOf("pageup") != -1) {
				_pageMenuDialog(-1);
			} else if (nav.indexOf("pagedown") != -1) {
				_pageMenuDialog(1);
			} else if (nav.indexOf("up") != -1) {
				if (_dialog.selectionIndex < 0)
					_setMenuDialogSelection(_dialog.options.length - 1);
				else
					_setMenuDialogSelection(_dialog.selectionIndex - 1);
			} else if (nav.indexOf("down") != -1) {
				if (_dialog.selectionIndex < 0)
					_setMenuDialogSelection(0);
				else
					_setMenuDialogSelection(_dialog.selectionIndex + 1);
			}
		} else if (kind == "color") {
			// SkyUI's ColorSwatch ignores held/repeated direction events.
			if (repeated)
				return;
			if (nav.indexOf("up") != -1) _adjustColor(-14);
			else if (nav.indexOf("down") != -1) _adjustColor(14);
			else if (nav.indexOf("left") != -1) _adjustColor(-1);
			else if (nav.indexOf("right") != -1) _adjustColor(1);
		}
	}

	private function _adjustSlider(direction:Number):Void
	{
		if (_dialog == null || _dialog.kind != "slider")
			return;
		_dialog.value = _lockSliderValue(
			_dialog.value + direction * _dialog.interval,
			_dialog.minimum, _dialog.maximum, _dialog.interval);
		_refreshSlider();
	}

	private function _adjustSliderPage(direction:Number):Void
	{
		if (_dialog == null || _dialog.kind != "slider")
			return;
		var range:Number = _dialog.maximum - _dialog.minimum;
		var pageStep:Number = range * 0.1;
		var raw:Number = _dialog.value + direction * pageStep;
		_dialog.value = _lockSliderValue(raw, _dialog.minimum,
			_dialog.maximum, _dialog.interval);
		_refreshSlider();
	}

	private function _lockSliderValue(raw:Number, minimum:Number,
		maximum:Number, interval:Number):Number
	{
		// Exact CLIK Slider.lockValue ordering: clamp, then zero-based snap.
		var value:Number = Math.max(minimum, Math.min(maximum, raw));
		return Math.round(value / interval) * interval;
	}

	private function _setSliderFromMouse(track:MovieClip):Void
	{
		var ratio:Number = Math.max(0, Math.min(1,
			(track._xmouse - SLIDER_TRACK_X) / SLIDER_TRACK_W));
		var raw:Number = _dialog.minimum + ratio *
			(_dialog.maximum - _dialog.minimum);
		var snapped:Number = _lockSliderValue(raw, _dialog.minimum,
			_dialog.maximum, _dialog.interval);
		if (snapped == _dialog.value)
			return;
		_dialog.value = snapped;
		_refreshSlider();
	}

	private function _setMenuDialogSelection(index:Number):Void
	{
		if (_dialog == null || _dialog.kind != "menu" ||
			_dialog.options.length == 0)
			return;
		var selectedIndex:Number = Math.max(0,
			Math.min(_dialog.options.length - 1, index));
		if (Number(_dialog.selectionIndex) == selectedIndex)
			return;
		_dialog.selectionIndex = selectedIndex;
		var previousScroll:Number = _dialog.scroll;
		if (selectedIndex < _dialog.scroll)
			_dialog.scroll = selectedIndex;
		else if (selectedIndex >= _dialog.scroll + 5)
			_dialog.scroll = selectedIndex - 4;
		if (previousScroll != _dialog.scroll)
			_renderDialog();
		else
			_refreshMenuSelection();
	}

	private function _clearMenuDialogSelection(index:Number):Void
	{
		if (_dialog == null || _dialog.kind != "menu" ||
			Number(_dialog.selectionIndex) != index)
			return;
		_dialog.selectionIndex = -1;
		_refreshMenuSelection();
	}

	private function _scrollMenuDialog(direction:Number):Void
	{
		if (_dialog == null || _dialog.kind != "menu")
			return;
		_menuDialogList.isMouseDrivenNav = true;
		var maximum:Number = Math.max(0, _dialog.options.length - 5);
		var scroll:Number = Math.max(0,
			Math.min(maximum, Number(_dialog.scroll) + direction));
		if (scroll == Number(_dialog.scroll))
			return;
		_dialog.scroll = scroll;
		_renderDialog();
	}

	private function _pageMenuDialog(direction:Number):Void
	{
		if (_dialog == null || _dialog.kind != "menu")
			return;
		var visible:Number = 5;
		var maximum:Number = Math.max(0, _dialog.options.length - visible);
		_dialog.scroll = Math.max(0, Math.min(maximum,
			Number(_dialog.scroll) + direction * visible));
		// SkyUI's ScrollingList page movement scrolls the renderer window and
		// clears its transient selection while preserving the committed entry.
		_dialog.selectionIndex = -1;
		_renderDialog();
	}

	private function _commitMenuDialogSelection(index:Number):Void
	{
		if (_dialog == null || _dialog.kind != "menu" ||
			_dialog.options.length == 0)
			return;
		if (index < 0)
			_dialog.selectionIndex = -1;
		else
			_dialog.selectionIndex = Math.min(_dialog.options.length - 1, index);
		_dialog.activeIndex = _dialog.selectionIndex;
		var previousScroll:Number = _dialog.scroll;
		if (_dialog.selectionIndex >= 0) {
			if (_dialog.selectionIndex < _dialog.scroll)
				_dialog.scroll = _dialog.selectionIndex;
			else if (_dialog.selectionIndex >= _dialog.scroll + 5)
				_dialog.scroll = _dialog.selectionIndex - 4;
		}
		if (previousScroll != _dialog.scroll)
			_renderDialog();
		else
			_refreshMenuSelection();
	}

	private function _adjustColor(direction:Number):Void
	{
		if (_dialog == null || _dialog.kind != "color")
			return;
		var index:Number = Number(_dialog.colorIndex);
		if (index < 0) {
			_selectColorIndex(direction < 0 ? _dialog.palette.length - 1 : 0);
			return;
		}
		var column:Number = index % 14;
		if (direction == -14 || direction == 14)
			index = index < 14 ? index + 14 : index - 14;
		else if (direction < 0)
			index = column > 0 ? index - 1 : index + 13;
		else
			index = column < 13 ? index + 1 : index - 13;
		_selectColorIndex(index);
	}

	private function _buildColorPalette():Array
	{
		// The public SkyUI MCM color contract is a two-by-fourteen palette.
		return [
			0x990033, 0xAD0073, 0xA17700, 0x803D0D, 0xBD4F19,
			0x007A87, 0x162274, 0x4F2D7F, 0x56364D, 0x618E02,
			0x008542, 0x5C4836, 0x999999, 0x000000,
			0xCC0033, 0xE86BA5, 0xEAAB00, 0xB88454, 0xE37222,
			0x99FFFF, 0x4060AF, 0x8C6CD0, 0x8F6678, 0x9EAB05,
			0x19B271, 0xAA9C8F, 0xCCCCCC, 0xFFFFFF
		];
	}

	private function _exactColorIndex(color:Number, palette:Array):Number
	{
		for (var i:Number = 0; i < palette.length; i++)
			if (Number(palette[i]) == Number(color))
				return i;
		return -1;
	}

	private function _selectColorIndex(index:Number):Void
	{
		if (_dialog == null || _dialog.kind != "color" ||
			_dialog.palette.length == 0)
			return;
		var selected:Number = Math.max(0,
			Math.min(_dialog.palette.length - 1, index));
		if (selected == Number(_dialog.colorIndex) &&
			Number(_dialog.color) == Number(_dialog.palette[selected]))
			return;
		_dialog.colorIndex = selected;
		_dialog.color = Number(_dialog.palette[_dialog.colorIndex]);
		_renderDialog();
	}

	private function _acceptDialog():Void
	{
		if (_dialog == null)
			return;
		var dialog:Object = _dialog;
		if (dialog.kind == "input") {
			if (_inputField != undefined)
				dialog.text = _inputField.text;
			_setTextInputEnabled(false);
		}
		if (dialog.browserAction != undefined) {
			_closeDialog(false);
			if (this._browser != undefined) {
				if (dialog.browserAction == "tools")
					this._browser.action(dialog.browserActions[dialog.activeIndex]);
				else this._browser.accept(dialog.browserAction, dialog.browserName, dialog.text);
			}
			return;
		}

		if (dialog.kind == "slider")
			MCMCompatUtil.sendModEvent("SKICP_sliderAccepted", null, dialog.value);
		else if (dialog.kind == "menu")
			MCMCompatUtil.sendModEvent("SKICP_menuAccepted", null,
				dialog.activeIndex);
		else if (dialog.kind == "color")
			MCMCompatUtil.sendModEvent("SKICP_colorAccepted", null, dialog.color);
		else if (dialog.kind == "input")
			MCMCompatUtil.sendModEvent("SKICP_inputAccepted", dialog.text, 0);
		else if (dialog.kind == "message")
			MCMCompatUtil.sendModEvent("SKICP_messageDialogClosed", null, 1);
		_closeDialog(false);
	}

	private function _cancelDialog():Void
	{
		if (_dialog == null)
			return;
		if (_dialog.browserAction != undefined) {
			_closeDialog(false);
			return;
		}
		var kind:String = _dialog.kind;
		var messageHasCancel:Boolean = kind == "message" && _dialog.cancelLabel != "";
		if (kind == "input")
			_setTextInputEnabled(false);
		if (kind == "message")
			MCMCompatUtil.sendModEvent("SKICP_messageDialogClosed", null,
				messageHasCancel ? 0 : 1);
		else
			MCMCompatUtil.sendModEvent("SKICP_dialogCanceled", null, 0);
		_closeDialog(false);
	}

	private function _closeDialog(sendCancel:Boolean):Void
	{
		_setTextInputEnabled(false);
		if (_dialog == null)
			return;
		var kind:String = _dialog.kind;
		var browserDialog:Boolean = _dialog.browserAction != undefined;
		if (sendCancel && !browserDialog) {
			if (kind == "message")
				MCMCompatUtil.sendModEvent("SKICP_messageDialogClosed", null, 0);
			else
				MCMCompatUtil.sendModEvent("SKICP_dialogCanceled", null, 0);
		}
		_sliderDragging = false;
		_dialog = null;
		if (browserDialog) _state = READY;
		_renderedDialog = null;
		_menuDialogList = undefined;
		_inputField = undefined;
		_modalLayer.removeMovieClip();
		_modalLayer = _chrome.createEmptyMovieClip("modalLayer", 100);
		_setContentDimmed(false);
		_restoreDialogFocus();
		_updateFooter();
	}
}
