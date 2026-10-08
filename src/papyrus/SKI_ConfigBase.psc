Scriptname SKI_ConfigBase extends SKI_QuestBase

; Stable Scaleform bridge used by existing SkyUI MCM scripts.
String Property JOURNAL_MENU = "Journal Menu" AutoReadOnly
String Property MENU_ROOT = "_root.ConfigPanelFader.configPanel" AutoReadOnly

Int Property STATE_DEFAULT = 0 AutoReadOnly
Int Property STATE_RESET = 1 AutoReadOnly
Int Property STATE_SLIDER = 2 AutoReadOnly
Int Property STATE_MENU = 3 AutoReadOnly
Int Property STATE_COLOR = 4 AutoReadOnly
Int Property STATE_INPUT = 5 AutoReadOnly

Int Property OPTION_TYPE_EMPTY = 0x00 AutoReadOnly
Int Property OPTION_TYPE_HEADER = 0x01 AutoReadOnly
Int Property OPTION_TYPE_TEXT = 0x02 AutoReadOnly
Int Property OPTION_TYPE_TOGGLE = 0x03 AutoReadOnly
Int Property OPTION_TYPE_SLIDER = 0x04 AutoReadOnly
Int Property OPTION_TYPE_MENU = 0x05 AutoReadOnly
Int Property OPTION_TYPE_COLOR = 0x06 AutoReadOnly
Int Property OPTION_TYPE_KEYMAP = 0x07 AutoReadOnly
Int Property OPTION_TYPE_INPUT = 0x08 AutoReadOnly

Int Property OPTION_FLAG_NONE = 0x00 AutoReadOnly
Int Property OPTION_FLAG_DISABLED = 0x01 AutoReadOnly
Int Property OPTION_FLAG_HIDDEN = 0x02 AutoReadOnly
Int Property OPTION_FLAG_WITH_UNMAP = 0x04 AutoReadOnly

Int Property LEFT_TO_RIGHT = 1 AutoReadOnly
Int Property TOP_TO_BOTTOM = 2 AutoReadOnly

; Field names intentionally match the established runtime ABI. MCM Helper reads these directly.
SKI_ConfigManager _configManager
Bool _initialized = False
Int _configID = -1
String _currentPage = ""
Int _currentPageNum = 0
Int _state = 0
Int _cursorPosition = 0
Int _cursorFillMode = 1

Int[] _optionFlagsBuf
String[] _textBuf
String[] _strValueBuf
Float[] _numValueBuf
Float[] _sliderParams
Int[] _menuParams
Int[] _colorParams
Int _activeOption = -1
String _infoText = ""
String _inputStartText = ""
Bool _messageResult = False
Bool _waitForMessage = False
String[] _stateOptionMap

String Property ModName Auto
String[] Property Pages Auto

String Property CurrentPage
	String Function Get()
		Return _currentPage
	EndFunction
EndProperty

Event OnInit()
	OnGameReload()
EndEvent

Event OnGameReload()
	If !_initialized
		_initialized = True
		InitializeDialogStorage()
		OnConfigInit()
		Debug.Trace(Self + ": MCM initialized")
	Else
		InitializeDialogStorage()
	EndIf

	RegisterForModEvent("SKICP_configManagerReady", "OnConfigManagerReady")
	RegisterForModEvent("SKICP_configManagerReset", "OnConfigManagerReset")
	CheckVersion()
EndEvent

; Extension callbacks ---------------------------------------------------------------

Event OnConfigInit()
EndEvent

Event OnConfigRegister()
EndEvent

Event OnConfigOpen()
EndEvent

Event OnConfigClose()
EndEvent

Event OnVersionUpdate(Int a_version)
EndEvent

Event OnPageReset(String a_page)
EndEvent

Event OnOptionHighlight(Int a_option)
EndEvent

Event OnOptionSelect(Int a_option)
EndEvent

Event OnOptionDefault(Int a_option)
EndEvent

Event OnOptionSliderOpen(Int a_option)
EndEvent

Event OnOptionSliderAccept(Int a_option, Float a_value)
EndEvent

Event OnOptionMenuOpen(Int a_option)
EndEvent

Event OnOptionMenuAccept(Int a_option, Int a_index)
EndEvent

Event OnOptionColorOpen(Int a_option)
EndEvent

Event OnOptionColorAccept(Int a_option, Int a_color)
EndEvent

Event OnOptionKeyMapChange(Int a_option, Int a_keyCode, String a_conflictControl, String a_conflictName)
EndEvent

; MCM Helper API version 4 input callbacks.
Event OnOptionInputOpen(Int a_option)
EndEvent

Event OnOptionInputAccept(Int a_option, String a_input)
EndEvent

Event OnHighlightST()
EndEvent

Event OnSelectST()
EndEvent

Event OnDefaultST()
EndEvent

Event OnSliderOpenST()
EndEvent

Event OnSliderAcceptST(Float a_value)
EndEvent

Event OnMenuOpenST()
EndEvent

Event OnMenuAcceptST(Int a_index)
EndEvent

Event OnColorOpenST()
EndEvent

Event OnColorAcceptST(Int a_color)
EndEvent

Event OnKeyMapChangeST(Int a_keyCode, String a_conflictControl, String a_conflictName)
EndEvent

Event OnInputOpenST()
EndEvent

Event OnInputAcceptST(String a_input)
EndEvent

; Registry and message events -------------------------------------------------------

Event OnConfigManagerReset(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	_configManager = None
	_configID = -1
EndEvent

Event OnConfigManagerReady(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	SKI_ConfigManager candidate = a_sender as SKI_ConfigManager
	If candidate == None
		Return
	EndIf

	; SkyUI's public registration ABI is RegisterMod. Always use that original
	; call when the manager announces readiness and let its identity scan dedupe
	; an existing entry. This also repairs a saved client whose cached manager
	; and slot survived while the manager's object array did not.
	SKI_ConfigManager previousManager = _configManager
	Int previousID = _configID
	Int assignedID = candidate.RegisterMod(Self, ModName)
	If assignedID >= 0
		_configManager = candidate
		_configID = assignedID
		; Repeated ready heartbeats must not repeatedly run provider callbacks.
		If previousManager != candidate || previousID != assignedID
			OnConfigRegister()
			Debug.Trace(Self + ": registered " + ModName + " with MCM")
		EndIf
	EndIf
EndEvent

Event OnMessageDialogClose(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _waitForMessage
		_messageResult = a_numArg as Bool
		_waitForMessage = False
	EndIf
EndEvent

; Public API ------------------------------------------------------------------------

Int Function GetVersion()
	Return 1
EndFunction

String Function GetCustomControl(Int a_keyCode)
	Return ""
EndFunction

Function ForcePageReset()
	UI.Invoke(JOURNAL_MENU, MENU_ROOT + ".forcePageReset")
EndFunction

Function SetTitleText(String a_text)
	UI.InvokeString(JOURNAL_MENU, MENU_ROOT + ".setTitleText", a_text)
EndFunction

Function SetInfoText(String a_text)
	_infoText = a_text
EndFunction

Function SetCursorPosition(Int a_position)
	If a_position < 128
		_cursorPosition = a_position
	EndIf
EndFunction

Function SetCursorFillMode(Int a_fillMode)
	If a_fillMode == LEFT_TO_RIGHT || a_fillMode == TOP_TO_BOTTOM
		_cursorFillMode = a_fillMode
	EndIf
EndFunction

Int Function AddEmptyOption()
	Return AddOption(OPTION_TYPE_EMPTY, "", "", 0.0, OPTION_FLAG_NONE)
EndFunction

Int Function AddHeaderOption(String a_text, Int a_flags = 0)
	Return AddOption(OPTION_TYPE_HEADER, a_text, "", 0.0, a_flags)
EndFunction

Int Function AddTextOption(String a_text, String a_value, Int a_flags = 0)
	Return AddOption(OPTION_TYPE_TEXT, a_text, a_value, 0.0, a_flags)
EndFunction

Int Function AddToggleOption(String a_text, Bool a_checked, Int a_flags = 0)
	Return AddOption(OPTION_TYPE_TOGGLE, a_text, "", a_checked as Int, a_flags)
EndFunction

Int Function AddSliderOption(String a_text, Float a_value, String a_formatString = "{0}", Int a_flags = 0)
	Return AddOption(OPTION_TYPE_SLIDER, a_text, a_formatString, a_value, a_flags)
EndFunction

Int Function AddMenuOption(String a_text, String a_value, Int a_flags = 0)
	Return AddOption(OPTION_TYPE_MENU, a_text, a_value, 0.0, a_flags)
EndFunction

Int Function AddColorOption(String a_text, Int a_color, Int a_flags = 0)
	Return AddOption(OPTION_TYPE_COLOR, a_text, "", a_color, a_flags)
EndFunction

Int Function AddKeyMapOption(String a_text, Int a_keyCode, Int a_flags = 0)
	Return AddOption(OPTION_TYPE_KEYMAP, a_text, "", a_keyCode, a_flags)
EndFunction

Int Function AddInputOption(String a_text, String a_value, Int a_flags = 0)
	Return AddOption(OPTION_TYPE_INPUT, a_text, a_value, 0.0, a_flags)
EndFunction

Function AddTextOptionST(String a_stateName, String a_text, String a_value, Int a_flags = 0)
	AddOptionST(a_stateName, OPTION_TYPE_TEXT, a_text, a_value, 0.0, a_flags)
EndFunction

Function AddToggleOptionST(String a_stateName, String a_text, Bool a_checked, Int a_flags = 0)
	AddOptionST(a_stateName, OPTION_TYPE_TOGGLE, a_text, "", a_checked as Int, a_flags)
EndFunction

Function AddSliderOptionST(String a_stateName, String a_text, Float a_value, String a_formatString = "{0}", Int a_flags = 0)
	AddOptionST(a_stateName, OPTION_TYPE_SLIDER, a_text, a_formatString, a_value, a_flags)
EndFunction

Function AddMenuOptionST(String a_stateName, String a_text, String a_value, Int a_flags = 0)
	AddOptionST(a_stateName, OPTION_TYPE_MENU, a_text, a_value, 0.0, a_flags)
EndFunction

Function AddColorOptionST(String a_stateName, String a_text, Int a_color, Int a_flags = 0)
	AddOptionST(a_stateName, OPTION_TYPE_COLOR, a_text, "", a_color, a_flags)
EndFunction

Function AddKeyMapOptionST(String a_stateName, String a_text, Int a_keyCode, Int a_flags = 0)
	AddOptionST(a_stateName, OPTION_TYPE_KEYMAP, a_text, "", a_keyCode, a_flags)
EndFunction

Function AddInputOptionST(String a_stateName, String a_text, String a_value, Int a_flags = 0)
	AddOptionST(a_stateName, OPTION_TYPE_INPUT, a_text, a_value, 0.0, a_flags)
EndFunction

Function LoadCustomContent(String a_source, Float a_x = 0.0, Float a_y = 0.0)
	Float[] placement = New Float[2]
	placement[0] = a_x
	placement[1] = a_y
	UI.InvokeFloatA(JOURNAL_MENU, MENU_ROOT + ".setCustomContentParams", placement)
	UI.InvokeString(JOURNAL_MENU, MENU_ROOT + ".loadCustomContent", a_source)
EndFunction

Function UnloadCustomContent()
	UI.Invoke(JOURNAL_MENU, MENU_ROOT + ".unloadCustomContent")
EndFunction

Function SetOptionFlags(Int a_option, Int a_flags, Bool a_noUpdate = False)
	If _state == STATE_RESET
		Error("Cannot set option flags while in OnPageReset(); pass flags to AddOption instead")
		Return
	EndIf

	Int index = GetOptionIndex(a_option)
	If index < 0
		Return
	EndIf

	Int optionType = _optionFlagsBuf[index] % 0x100
	_optionFlagsBuf[index] = optionType + (a_flags * 0x100)

	Int[] params = New Int[2]
	params[0] = index
	params[1] = a_flags
	UI.InvokeIntA(JOURNAL_MENU, MENU_ROOT + ".setOptionFlags", params)
	If !a_noUpdate
		UI.Invoke(JOURNAL_MENU, MENU_ROOT + ".invalidateOptionData")
	EndIf
EndFunction

Function SetTextOptionValue(Int a_option, String a_value, Bool a_noUpdate = False)
	Int index = RequireOptionType(a_option, OPTION_TYPE_TEXT, "text")
	If index >= 0
		SetOptionStrValue(index, a_value, a_noUpdate)
	EndIf
EndFunction

Function SetToggleOptionValue(Int a_option, Bool a_checked, Bool a_noUpdate = False)
	Int index = RequireOptionType(a_option, OPTION_TYPE_TOGGLE, "toggle")
	If index >= 0
		SetOptionNumValue(index, a_checked as Int, a_noUpdate)
	EndIf
EndFunction

Function SetSliderOptionValue(Int a_option, Float a_value, String a_formatString = "{0}", Bool a_noUpdate = False)
	Int index = RequireOptionType(a_option, OPTION_TYPE_SLIDER, "slider")
	If index >= 0
		SetOptionValues(index, a_formatString, a_value, a_noUpdate)
	EndIf
EndFunction

Function SetMenuOptionValue(Int a_option, String a_value, Bool a_noUpdate = False)
	Int index = RequireOptionType(a_option, OPTION_TYPE_MENU, "menu")
	If index >= 0
		SetOptionStrValue(index, a_value, a_noUpdate)
	EndIf
EndFunction

Function SetColorOptionValue(Int a_option, Int a_color, Bool a_noUpdate = False)
	Int index = RequireOptionType(a_option, OPTION_TYPE_COLOR, "color")
	If index >= 0
		SetOptionNumValue(index, a_color, a_noUpdate)
	EndIf
EndFunction

Function SetKeyMapOptionValue(Int a_option, Int a_keyCode, Bool a_noUpdate = False)
	Int index = RequireOptionType(a_option, OPTION_TYPE_KEYMAP, "keymap")
	If index >= 0
		SetOptionNumValue(index, a_keyCode, a_noUpdate)
	EndIf
EndFunction

Function SetInputOptionValue(Int a_option, String a_value, Bool a_noUpdate = False)
	Int index = RequireOptionType(a_option, OPTION_TYPE_INPUT, "input")
	If index >= 0
		SetOptionStrValue(index, a_value, a_noUpdate)
	EndIf
EndFunction

Function SetOptionFlagsST(Int a_flags, Bool a_noUpdate = False, String a_stateName = "")
	If _state == STATE_RESET
		Error("Cannot set option flags while in OnPageReset(); pass flags to AddOptionST instead")
		Return
	EndIf
	Int index = GetStateOptionIndex(a_stateName)
	If index >= 0
		SetOptionFlags(index, a_flags, a_noUpdate)
	Else
		Error("Cannot use SetOptionFlagsST outside a valid option state")
	EndIf
EndFunction

Function SetTextOptionValueST(String a_value, Bool a_noUpdate = False, String a_stateName = "")
	Int index = GetStateOptionIndex(a_stateName)
	If index >= 0
		SetTextOptionValue(index, a_value, a_noUpdate)
	Else
		Error("Cannot use SetTextOptionValueST outside a valid option state")
	EndIf
EndFunction

Function SetToggleOptionValueST(Bool a_checked, Bool a_noUpdate = False, String a_stateName = "")
	Int index = GetStateOptionIndex(a_stateName)
	If index >= 0
		SetToggleOptionValue(index, a_checked, a_noUpdate)
	Else
		Error("Cannot use SetToggleOptionValueST outside a valid option state")
	EndIf
EndFunction

Function SetSliderOptionValueST(Float a_value, String a_formatString = "{0}", Bool a_noUpdate = False, String a_stateName = "")
	Int index = GetStateOptionIndex(a_stateName)
	If index >= 0
		SetSliderOptionValue(index, a_value, a_formatString, a_noUpdate)
	Else
		Error("Cannot use SetSliderOptionValueST outside a valid option state")
	EndIf
EndFunction

Function SetMenuOptionValueST(String a_value, Bool a_noUpdate = False, String a_stateName = "")
	Int index = GetStateOptionIndex(a_stateName)
	If index >= 0
		SetMenuOptionValue(index, a_value, a_noUpdate)
	Else
		Error("Cannot use SetMenuOptionValueST outside a valid option state")
	EndIf
EndFunction

Function SetColorOptionValueST(Int a_color, Bool a_noUpdate = False, String a_stateName = "")
	Int index = GetStateOptionIndex(a_stateName)
	If index >= 0
		SetColorOptionValue(index, a_color, a_noUpdate)
	Else
		Error("Cannot use SetColorOptionValueST outside a valid option state")
	EndIf
EndFunction

Function SetKeyMapOptionValueST(Int a_keyCode, Bool a_noUpdate = False, String a_stateName = "")
	Int index = GetStateOptionIndex(a_stateName)
	If index >= 0
		SetKeyMapOptionValue(index, a_keyCode, a_noUpdate)
	Else
		Error("Cannot use SetKeyMapOptionValueST outside a valid option state")
	EndIf
EndFunction

Function SetInputOptionValueST(String a_value, Bool a_noUpdate = False, String a_stateName = "")
	Int index = GetStateOptionIndex(a_stateName)
	If index >= 0
		SetInputOptionValue(index, a_value, a_noUpdate)
	Else
		Error("Cannot use SetInputOptionValueST outside a valid option state")
	EndIf
EndFunction

Function SetSliderDialogStartValue(Float a_value)
	If _state != STATE_SLIDER
		Error("Cannot set slider dialog params outside OnOptionSliderOpen()")
		Return
	EndIf
	_sliderParams[0] = a_value
EndFunction

Function SetSliderDialogDefaultValue(Float a_value)
	If _state != STATE_SLIDER
		Error("Cannot set slider dialog params outside OnOptionSliderOpen()")
		Return
	EndIf
	_sliderParams[1] = a_value
EndFunction

Function SetSliderDialogRange(Float a_minValue, Float a_maxValue)
	If _state != STATE_SLIDER
		Error("Cannot set slider dialog params outside OnOptionSliderOpen()")
		Return
	EndIf
	_sliderParams[2] = a_minValue
	_sliderParams[3] = a_maxValue
EndFunction

Function SetSliderDialogInterval(Float a_value)
	If _state != STATE_SLIDER
		Error("Cannot set slider dialog params outside OnOptionSliderOpen()")
		Return
	EndIf
	_sliderParams[4] = a_value
EndFunction

Function SetMenuDialogStartIndex(Int a_value)
	If _state != STATE_MENU
		Error("Cannot set menu dialog params outside OnOptionMenuOpen()")
		Return
	EndIf
	_menuParams[0] = a_value
EndFunction

Function SetMenuDialogDefaultIndex(Int a_value)
	If _state != STATE_MENU
		Error("Cannot set menu dialog params outside OnOptionMenuOpen()")
		Return
	EndIf
	_menuParams[1] = a_value
EndFunction

Function SetMenuDialogOptions(String[] a_options)
	If _state != STATE_MENU
		Error("Cannot set menu dialog params outside OnOptionMenuOpen()")
		Return
	EndIf
	UI.InvokeStringA(JOURNAL_MENU, MENU_ROOT + ".setMenuDialogOptions", a_options)
EndFunction

Function SetColorDialogStartColor(Int a_color)
	If _state != STATE_COLOR
		Error("Cannot set color dialog params outside OnOptionColorOpen()")
		Return
	EndIf
	_colorParams[0] = a_color
EndFunction

Function SetColorDialogDefaultColor(Int a_color)
	If _state != STATE_COLOR
		Error("Cannot set color dialog params outside OnOptionColorOpen()")
		Return
	EndIf
	_colorParams[1] = a_color
EndFunction

Function SetInputDialogStartText(String a_text)
	If _state != STATE_INPUT
		Error("Cannot set input dialog params outside OnOptionInputOpen()")
		Return
	EndIf
	_inputStartText = a_text
EndFunction

Bool Function ShowMessage(String a_message, Bool a_withCancel = True, String a_acceptLabel = "$Accept", String a_cancelLabel = "$Cancel")
	If _waitForMessage
		Error("ShowMessage called while another MCM message is open")
		Return False
	EndIf

	_waitForMessage = True
	_messageResult = False
	String[] params = New String[3]
	params[0] = a_message
	params[1] = a_acceptLabel
	If a_withCancel
		params[2] = a_cancelLabel
	Else
		params[2] = ""
	EndIf

	RegisterForModEvent("SKICP_messageDialogClosed", "OnMessageDialogClose")
	UI.InvokeStringA(JOURNAL_MENU, MENU_ROOT + ".showMessageDialog", params)
	While _waitForMessage
		Utility.WaitMenuMode(0.1)
	EndWhile
	UnregisterForModEvent("SKICP_messageDialogClosed")
	Return _messageResult
EndFunction

; Manager/UI bridge ---------------------------------------------------------------

Function OpenConfig()
	; A saved provider can be registered/initialized without dialog storage.
	; Repair on use, even when a mod does not forward OnGameReload to its parent.
	InitializeDialogStorage()
	AllocateOptionBuffers()
	SetPage("", -1)
	OnConfigOpen()
	UI.InvokeStringA(JOURNAL_MENU, MENU_ROOT + ".setPageNames", Pages)
EndFunction

Function CloseConfig()
	OnConfigClose()
	If _optionFlagsBuf != None && _optionFlagsBuf.Length == 128
		ClearOptionBuffers()
	EndIf
	_waitForMessage = False
	_activeOption = -1
	_state = STATE_DEFAULT
	ReleaseOptionBuffers()
EndFunction

Function SetPage(String a_page, Int a_index)
	If _optionFlagsBuf == None || _optionFlagsBuf.Length != 128
		AllocateOptionBuffers()
	EndIf

	_currentPage = a_page
	_currentPageNum = a_index + 1
	If a_page == ""
		SetTitleText(ModName)
	Else
		SetTitleText(a_page)
	EndIf

	ClearOptionBuffers()
	_state = STATE_RESET
	OnPageReset(a_page)
	_state = STATE_DEFAULT
	WriteOptionBuffers()
EndFunction

Int Function AddOption(Int a_optionType, String a_text, String a_strValue, Float a_numValue, Int a_flags)
	If _state != STATE_RESET
		Error("Cannot add option " + a_text + " outside OnPageReset()")
		Return -1
	EndIf
	If _cursorPosition < 0 || _cursorPosition >= 128
		Return -1
	EndIf

	Int position = _cursorPosition
	_optionFlagsBuf[position] = a_optionType + (a_flags * 0x100)
	_textBuf[position] = a_text
	_strValueBuf[position] = a_strValue
	_numValueBuf[position] = a_numValue

	_cursorPosition += _cursorFillMode
	If _cursorPosition >= 128
		_cursorPosition = -1
	EndIf
	Return position + (_currentPageNum * 0x100)
EndFunction

Function AddOptionST(String a_stateName, Int a_optionType, String a_text, String a_strValue, Float a_numValue, Int a_flags)
	If a_stateName == ""
		Error("State option name cannot be empty")
		Return
	EndIf
	If _stateOptionMap.Find(a_stateName) >= 0
		Error("State option name " + a_stateName + " is already in use")
		Return
	EndIf

	Int optionID = AddOption(a_optionType, a_text, a_strValue, a_numValue, a_flags)
	If optionID < 0
		Return
	EndIf
	Int index = optionID % 0x100
	If _stateOptionMap[index] != ""
		Error("State option index " + index + " already in use")
		Return
	EndIf
	_stateOptionMap[index] = a_stateName
EndFunction

Int Function GetStateOptionIndex(String a_stateName)
	If _stateOptionMap == None || _stateOptionMap.Length != 128
		Return -1
	EndIf
	String stateName = a_stateName
	If stateName == ""
		stateName = GetState()
	EndIf
	If stateName == ""
		Return -1
	EndIf
	Return _stateOptionMap.Find(stateName)
EndFunction

Function WriteOptionBuffers()
	Int optionCount = 0
	Int i = 0
	While i < 128
		If _optionFlagsBuf[i] != OPTION_TYPE_EMPTY
			optionCount = i + 1
		EndIf
		i += 1
	EndWhile

	UI.InvokeIntA(JOURNAL_MENU, MENU_ROOT + ".setOptionFlagsBuffer", _optionFlagsBuf)
	UI.InvokeStringA(JOURNAL_MENU, MENU_ROOT + ".setOptionTextBuffer", _textBuf)
	UI.InvokeStringA(JOURNAL_MENU, MENU_ROOT + ".setOptionStrValueBuffer", _strValueBuf)
	UI.InvokeFloatA(JOURNAL_MENU, MENU_ROOT + ".setOptionNumValueBuffer", _numValueBuf)
	UI.InvokeInt(JOURNAL_MENU, MENU_ROOT + ".flushOptionBuffers", optionCount)
EndFunction

Function ClearOptionBuffers()
	If _optionFlagsBuf == None || _optionFlagsBuf.Length != 128
		Return
	EndIf
	Int i = 0
	While i < 128
		_optionFlagsBuf[i] = OPTION_TYPE_EMPTY
		_textBuf[i] = ""
		_strValueBuf[i] = ""
		_numValueBuf[i] = 0.0
		_stateOptionMap[i] = ""
		i += 1
	EndWhile
	_cursorPosition = 0
	_cursorFillMode = LEFT_TO_RIGHT
EndFunction

Function SetOptionStrValue(Int a_index, String a_strValue, Bool a_noUpdate)
	If _state == STATE_RESET
		Error("Cannot modify option data inside OnPageReset()")
		Return
	EndIf
	Int index = GetOptionIndex(a_index)
	If index < 0
		Return
	EndIf

	_strValueBuf[index] = a_strValue
	UI.SetInt(JOURNAL_MENU, MENU_ROOT + ".optionCursorIndex", index)
	UI.SetString(JOURNAL_MENU, MENU_ROOT + ".optionCursor.strValue", a_strValue)
	If !a_noUpdate
		UI.Invoke(JOURNAL_MENU, MENU_ROOT + ".invalidateOptionData")
	EndIf
EndFunction

Function SetOptionNumValue(Int a_index, Float a_numValue, Bool a_noUpdate)
	If _state == STATE_RESET
		Error("Cannot modify option data inside OnPageReset()")
		Return
	EndIf
	Int index = GetOptionIndex(a_index)
	If index < 0
		Return
	EndIf

	_numValueBuf[index] = a_numValue
	UI.SetInt(JOURNAL_MENU, MENU_ROOT + ".optionCursorIndex", index)
	UI.SetFloat(JOURNAL_MENU, MENU_ROOT + ".optionCursor.numValue", a_numValue)
	If !a_noUpdate
		UI.Invoke(JOURNAL_MENU, MENU_ROOT + ".invalidateOptionData")
	EndIf
EndFunction

Function SetOptionValues(Int a_index, String a_strValue, Float a_numValue, Bool a_noUpdate)
	If _state == STATE_RESET
		Error("Cannot modify option data inside OnPageReset()")
		Return
	EndIf
	Int index = GetOptionIndex(a_index)
	If index < 0
		Return
	EndIf

	_strValueBuf[index] = a_strValue
	_numValueBuf[index] = a_numValue
	UI.SetInt(JOURNAL_MENU, MENU_ROOT + ".optionCursorIndex", index)
	UI.SetString(JOURNAL_MENU, MENU_ROOT + ".optionCursor.strValue", a_strValue)
	UI.SetFloat(JOURNAL_MENU, MENU_ROOT + ".optionCursor.numValue", a_numValue)
	If !a_noUpdate
		UI.Invoke(JOURNAL_MENU, MENU_ROOT + ".invalidateOptionData")
	EndIf
EndFunction

Function RequestSliderDialogData(Int a_index)
	If !IsValidPageIndex(a_index)
		Return
	EndIf
	; This is scratch storage for this request, not saved mod settings. Always
	; create it before defaults and callbacks (including MCM Helper natives).
	_sliderParams = New Float[5]
	_activeOption = a_index + (_currentPageNum * 0x100)
	_sliderParams[0] = 0.0
	_sliderParams[1] = 0.0
	_sliderParams[2] = 0.0
	_sliderParams[3] = 1.0
	_sliderParams[4] = 1.0
	_state = STATE_SLIDER

	String optionState = _stateOptionMap[a_index]
	If optionState == ""
		OnOptionSliderOpen(_activeOption)
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnSliderOpenST()
		GotoState(previousState)
	EndIf
	_state = STATE_DEFAULT
	UI.InvokeFloatA(JOURNAL_MENU, MENU_ROOT + ".setSliderDialogParams", _sliderParams)
EndFunction

Function RequestMenuDialogData(Int a_index)
	If !IsValidPageIndex(a_index)
		Return
	EndIf
	_menuParams = New Int[2]
	_activeOption = a_index + (_currentPageNum * 0x100)
	_menuParams[0] = -1
	_menuParams[1] = -1
	_state = STATE_MENU

	String optionState = _stateOptionMap[a_index]
	If optionState == ""
		OnOptionMenuOpen(_activeOption)
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnMenuOpenST()
		GotoState(previousState)
	EndIf
	_state = STATE_DEFAULT
	UI.InvokeIntA(JOURNAL_MENU, MENU_ROOT + ".setMenuDialogParams", _menuParams)
EndFunction

Function RequestColorDialogData(Int a_index)
	If !IsValidPageIndex(a_index)
		Return
	EndIf
	_colorParams = New Int[2]
	_activeOption = a_index + (_currentPageNum * 0x100)
	_colorParams[0] = -1
	_colorParams[1] = -1
	_state = STATE_COLOR

	String optionState = _stateOptionMap[a_index]
	If optionState == ""
		OnOptionColorOpen(_activeOption)
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnColorOpenST()
		GotoState(previousState)
	EndIf
	_state = STATE_DEFAULT
	UI.InvokeIntA(JOURNAL_MENU, MENU_ROOT + ".setColorDialogParams", _colorParams)
EndFunction

Function RequestInputDialogData(Int a_index)
	If !IsValidPageIndex(a_index)
		Return
	EndIf
	_activeOption = a_index + (_currentPageNum * 0x100)
	_inputStartText = ""
	_state = STATE_INPUT

	String optionState = _stateOptionMap[a_index]
	If optionState == ""
		OnOptionInputOpen(_activeOption)
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnInputOpenST()
		GotoState(previousState)
	EndIf
	_state = STATE_DEFAULT
	UI.InvokeString(JOURNAL_MENU, MENU_ROOT + ".setInputDialogParams", _inputStartText)
EndFunction

Function SetSliderValue(Float a_value)
	If _activeOption < 0
		Return
	EndIf
	Int optionID = _activeOption
	Int index = optionID % 0x100
	If !IsValidPageIndex(index)
		_activeOption = -1
		Return
	EndIf

	String optionState = _stateOptionMap[index]
	If optionState == ""
		OnOptionSliderAccept(optionID, a_value)
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnSliderAcceptST(a_value)
		GotoState(previousState)
	EndIf
	_activeOption = -1
EndFunction

Function SetMenuIndex(Int a_index)
	If _activeOption < 0
		Return
	EndIf
	Int optionID = _activeOption
	Int index = optionID % 0x100
	If !IsValidPageIndex(index)
		_activeOption = -1
		Return
	EndIf

	String optionState = _stateOptionMap[index]
	If optionState == ""
		OnOptionMenuAccept(optionID, a_index)
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnMenuAcceptST(a_index)
		GotoState(previousState)
	EndIf
	_activeOption = -1
EndFunction

Function SetColorValue(Int a_color)
	If _activeOption < 0
		Return
	EndIf
	Int optionID = _activeOption
	Int index = optionID % 0x100
	If !IsValidPageIndex(index)
		_activeOption = -1
		Return
	EndIf

	String optionState = _stateOptionMap[index]
	If optionState == ""
		OnOptionColorAccept(optionID, a_color)
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnColorAcceptST(a_color)
		GotoState(previousState)
	EndIf
	_activeOption = -1
EndFunction

Function SetInputText(String a_text)
	If _activeOption < 0
		Return
	EndIf
	Int optionID = _activeOption
	Int index = optionID % 0x100
	If !IsValidPageIndex(index)
		_activeOption = -1
		Return
	EndIf

	String optionState = _stateOptionMap[index]
	If optionState == ""
		OnOptionInputAccept(optionID, a_text)
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnInputAcceptST(a_text)
		GotoState(previousState)
	EndIf
	_activeOption = -1
EndFunction

Function SelectOption(Int a_index)
	If !IsValidPageIndex(a_index)
		Return
	EndIf
	String optionState = _stateOptionMap[a_index]
	If optionState == ""
		OnOptionSelect(a_index + (_currentPageNum * 0x100))
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnSelectST()
		GotoState(previousState)
	EndIf
EndFunction

Function ResetOption(Int a_index)
	If !IsValidPageIndex(a_index)
		Return
	EndIf
	String optionState = _stateOptionMap[a_index]
	If optionState == ""
		OnOptionDefault(a_index + (_currentPageNum * 0x100))
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnDefaultST()
		GotoState(previousState)
	EndIf
EndFunction

Function HighlightOption(Int a_index)
	; Default hooks preserve the SkyUI behavior. Only OpenMCM_ConfigBase opts
	; into automatic help and page-scoped publication after author callbacks.
	Int openmcmToken = OpenMCM_CapturePageToken()
	_infoText = OpenMCM_DefaultHelp(a_index)
	If IsValidPageIndex(a_index)
		String optionState = _stateOptionMap[a_index]
		If optionState == ""
			OnOptionHighlight(a_index + (_currentPageNum * 0x100))
		Else
			String previousState = GetState()
			GotoState(optionState)
			OnHighlightST()
			GotoState(previousState)
		EndIf
	EndIf
	OpenMCM_PublishHelp(a_index, _infoText, openmcmToken)
EndFunction

; Additive internal extension hooks. Do not override these in menu providers.
; No existing fields, option IDs, callbacks, or SkyUI API versions change.
Int Function OpenMCM_GetConfigID()
	Return _configID
EndFunction

Function OpenMCM_ClearOptionState(Int a_option)
	Int index = a_option % 0x100
	If a_option >= 0 && (a_option / 0x100) == _currentPageNum && IsValidPageIndex(index)
		_stateOptionMap[index] = ""
	EndIf
EndFunction

Int Function OpenMCM_CapturePageToken()
	Return 0
EndFunction

String Function OpenMCM_DefaultHelp(Int a_index)
	Return ""
EndFunction

Function OpenMCM_PublishHelp(Int a_index, String a_text, Int a_token)
	UI.InvokeString(JOURNAL_MENU, MENU_ROOT + ".setInfoText", a_text)
EndFunction

Function RemapKey(Int a_index, Int a_keyCode, String a_conflictControl, String a_conflictName)
	If !IsValidPageIndex(a_index)
		Return
	EndIf
	String optionState = _stateOptionMap[a_index]
	If optionState == ""
		OnOptionKeyMapChange(a_index + (_currentPageNum * 0x100), a_keyCode, a_conflictControl, a_conflictName)
	Else
		String previousState = GetState()
		GotoState(optionState)
		OnKeyMapChangeST(a_keyCode, a_conflictControl, a_conflictName)
		GotoState(previousState)
	EndIf
EndFunction

; Internal helpers ------------------------------------------------------------------

Function InitializeDialogStorage()
	; Match SkyUI's explicit allocation. Do not trust the saved _initialized
	; flag or old nullable buffers. These nine slots are temporary dialog data;
	; the provider supplies its real values in each dialog-open callback.
	_sliderParams = New Float[5]
	_menuParams = New Int[2]
	_colorParams = New Int[2]
	If _optionFlagsBuf == None || _textBuf == None || _strValueBuf == None || _numValueBuf == None || _stateOptionMap == None
		ReleaseOptionBuffers()
	EndIf
EndFunction

Function AllocateOptionBuffers()
	_optionFlagsBuf = New Int[128]
	_textBuf = New String[128]
	_strValueBuf = New String[128]
	_numValueBuf = New Float[128]
	_stateOptionMap = New String[128]
EndFunction

Function ReleaseOptionBuffers()
	_optionFlagsBuf = New Int[1]
	_textBuf = New String[1]
	_strValueBuf = New String[1]
	_numValueBuf = New Float[1]
	_stateOptionMap = New String[1]
EndFunction

Bool Function IsValidPageIndex(Int a_index)
	If a_index < 0 || a_index >= 128
		Return False
	EndIf
	If _optionFlagsBuf == None || _optionFlagsBuf.Length != 128
		Return False
	EndIf
	Return True
EndFunction

Int Function GetOptionIndex(Int a_option)
	If a_option < 0
		Error("Invalid option ID " + a_option)
		Return -1
	EndIf
	Int index = a_option % 0x100
	If !IsValidPageIndex(index)
		Error("Option data is unavailable for ID " + a_option)
		Return -1
	EndIf
	Return index
EndFunction

Int Function RequireOptionType(Int a_option, Int a_expectedType, String a_typeName)
	Int index = GetOptionIndex(a_option)
	If index < 0
		Return -1
	EndIf
	If (_optionFlagsBuf[index] % 0x100) == a_expectedType
		Return index
	EndIf

	String pageName = ""
	Int pageIndex = (a_option / 0x100) - 1
	If Pages != None
		If pageIndex >= 0 && pageIndex < Pages.Length
			pageName = Pages[pageIndex]
		EndIf
	EndIf
	Error("Option type mismatch. Expected " + a_typeName + " option, page \"" + pageName + "\", index " + index)
	Return -1
EndFunction

Function Error(String a_msg)
	Debug.Trace(Self + " ERROR: " + a_msg)
EndFunction

; Retained because it is present in the published SDK header.
Function Guard()
	Debug.Trace(Self + ": compatibility Guard() called")
EndFunction
