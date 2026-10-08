Scriptname OpenMCM_ConfigBase extends SKI_ConfigBase

; Basic SDK adapter for MCM Bridge. Bridge owns registration, admission,
; rendering and all ordinary SkyUI callbacks. No Journal or native replacement.
; Original OpenMCM code: GPL-3.0-or-later; see the accompanying LICENSE.txt.
; Keep API 1 signatures and saved field names/types, but never mint live tokens.
String[] _openmcmKeys
String[] _openmcmHelp
Int[] _openmcmIDs
Int[] _openmcmTypes
Int _openmcmPageIndex = -2
Int _openmcmProviderID = -1
Int _openmcmPageToken = 0
Int _openmcmHostToken = 0
Int _openmcmGeneration = 0
Bool _openmcmBuilding = False

; Adapter-only cursor/state mirrors are not Bridge's private storage.
Int _openmcmBridgeCursor = 0
Int _openmcmBridgeFillMode = 1
String[] _openmcmBridgeStates

Event OnGameReload()
	OpenMCM_ClearPage()
	Parent.OnGameReload()
EndEvent

Event OnConfigManagerReset(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	OpenMCM_ClearPage()
	Parent.OnConfigManagerReset(a_eventName, a_strArg, a_numArg, a_sender)
EndEvent

Function CloseConfig()
	OpenMCM_ClearPage()
	Parent.CloseConfig()
EndFunction

Function SetPage(String a_page, Int a_index)
	OpenMCM_ClearPage()
	_openmcmPageIndex = a_index
	_openmcmBuilding = True
	; Parent owns native admission, calls ClearOptionBuffers/OnPageReset and
	; publishes the page. Do not copy its admission code into this script.
	Parent.SetPage(a_page, a_index)
	_openmcmBuilding = False
EndFunction

Function ClearOptionBuffers()
	Parent.ClearOptionBuffers()
	_openmcmKeys = New String[128]
	_openmcmHelp = New String[128]
	_openmcmIDs = New Int[128]
	_openmcmTypes = New Int[128]
	_openmcmBridgeStates = New String[128]
	_openmcmBridgeCursor = 0
	_openmcmBridgeFillMode = 1
EndFunction

Function SetCursorPosition(Int a_position)
	Parent.SetCursorPosition(a_position)
	If a_position >= -1 && a_position < 128
		_openmcmBridgeCursor = a_position
	EndIf
EndFunction

Function SetCursorFillMode(Int a_fillMode)
	Parent.SetCursorFillMode(a_fillMode)
	If a_fillMode == LEFT_TO_RIGHT || a_fillMode == TOP_TO_BOTTOM
		_openmcmBridgeFillMode = a_fillMode
	EndIf
EndFunction

; Bridge routes BOTH ordinary and ST additions through this method. Keeping
; only an AddOption override would miss the state-based controls entirely.
Int Function BridgeAddOption(Int a_type, String a_label, String a_text, Float a_number, Int a_flags, String a_state)
	If _openmcmBuilding && _openmcmBridgeCursor >= 0 && _openmcmBridgeCursor < 128 && _openmcmBridgeStates != None && _openmcmBridgeStates.Length == 128
		; Bridge retains the previous ST state when an ordinary row overwrites
		; its slot. Reject BEFORE touching the host so the old row remains valid.
		; Rebuild the page first to replace an ST control with an ordinary one.
		If a_state == "" && _openmcmBridgeStates[_openmcmBridgeCursor] != ""
			OpenMCM_Error("Cannot replace an ST option with an ordinary option in-place; rebuild the page first")
			Return -1
		EndIf
	EndIf
	Int optionID = Parent.BridgeAddOption(a_type, a_label, a_text, a_number, a_flags, a_state)
	If optionID >= 0 && _openmcmBuilding
		Int index = optionID % 0x100
		If index >= 128 || (optionID / 0x100) != (_openmcmPageIndex + 1) || _openmcmIDs == None || _openmcmIDs.Length != 128
			OpenMCM_Error("Bridge returned an invalid option ID " + optionID)
			Return -1
		EndIf
		; Cursor rewinds invalidate old names/help, including unnamed replacements.
		_openmcmKeys[index] = ""
		_openmcmHelp[index] = ""
		_openmcmIDs[index] = optionID
		_openmcmTypes[index] = a_type
		_openmcmBridgeStates[index] = a_state
		_openmcmBridgeCursor = index + _openmcmBridgeFillMode
		If _openmcmBridgeCursor >= 128
			_openmcmBridgeCursor = -1
		EndIf
	EndIf
	Return optionID
EndFunction

Int Function AddOption(Int a_optionType, String a_text, String a_strValue, Float a_numValue, Int a_flags)
	; The parent's call reaches the BridgeAddOption override above.
	Return Parent.AddOption(a_optionType, a_text, a_strValue, a_numValue, a_flags)
EndFunction

Bool Function BindOption(String a_key, Int a_option, String a_help = "")
	If !OpenMCM_CanBind(a_key)
		Return False
	EndIf
	Int index = OpenMCM_ResolveID(a_option)
	If index < 0
		OpenMCM_Error("Cannot bind '" + a_key + "': invalid option ID " + a_option)
		Return False
	EndIf
	If _openmcmKeys[index] != ""
		OpenMCM_Error("Option " + a_option + " is already bound to '" + _openmcmKeys[index] + "'")
		Return False
	EndIf
	_openmcmKeys[index] = a_key
	; Stored for signature compatibility only. Automatic help is unsupported.
	_openmcmHelp[index] = a_help
	Return True
EndFunction

Bool Function BindStateOption(String a_key, String a_stateName, String a_help = "")
	Int index = GetStateOptionIndex(a_stateName)
	If index < 0
		OpenMCM_Error("Cannot bind '" + a_key + "': unknown option state '" + a_stateName + "'")
		Return False
	EndIf
	Return BindOption(a_key, index + ((_openmcmPageIndex + 1) * 0x100), a_help)
EndFunction

Int Function GetOptionID(String a_key)
	Int index = OpenMCM_FindKey(a_key)
	If index < 0
		Return -1
	EndIf
	Return _openmcmIDs[index]
EndFunction

; Do not use Bridge's config-session token as an OpenMCM page token. Its
; lifetime/ownership contract does not provide the API 1 live-operation guard.
Int Function GetPageToken()
	Return 0
EndFunction

Bool Function IsPageTokenValid(Int a_token)
	Return False
EndFunction

Bool Function OpenMCM_IsPageContextValid(Int a_token)
	Return False
EndFunction

Bool Function SetOptionLabel(String a_key, String a_text, Int a_token)
	Return False
EndFunction

Bool Function SetOptionText(String a_key, String a_text, Int a_token)
	Return False
EndFunction

Bool Function SetOptionHelp(String a_key, String a_text, Int a_token)
	Return False
EndFunction

Bool Function SetLiveInfoText(String a_text, Int a_token)
	Return False
EndFunction

Bool Function SetCurrentPage(String a_page, Int a_token)
	Return False
EndFunction

Bool Function SetOptionsEnabled(String[] a_keys, Bool a_enabled, Int a_token)
	Return False
EndFunction

; These controls retain normal SkyUI types, IDs and typed callback setters.
Int Function AddNamedHeader(String a_key, String a_text, String a_help = "", Int a_flags = 0)
	Return OpenMCM_AddNamed(a_key, OPTION_TYPE_HEADER, a_text, "", 0.0, a_help, a_flags)
EndFunction

Int Function AddNamedText(String a_key, String a_text, String a_value, String a_help = "", Int a_flags = 0)
	Return OpenMCM_AddNamed(a_key, OPTION_TYPE_TEXT, a_text, a_value, 0.0, a_help, a_flags)
EndFunction

Int Function AddNamedToggle(String a_key, String a_text, Bool a_checked, String a_help = "", Int a_flags = 0)
	Return OpenMCM_AddNamed(a_key, OPTION_TYPE_TOGGLE, a_text, "", a_checked as Int, a_help, a_flags)
EndFunction

Int Function AddNamedSlider(String a_key, String a_text, Float a_value, String a_formatString = "{0}", String a_help = "", Int a_flags = 0)
	Return OpenMCM_AddNamed(a_key, OPTION_TYPE_SLIDER, a_text, a_formatString, a_value, a_help, a_flags)
EndFunction

Int Function AddNamedMenu(String a_key, String a_text, String a_value, String a_help = "", Int a_flags = 0)
	Return OpenMCM_AddNamed(a_key, OPTION_TYPE_MENU, a_text, a_value, 0.0, a_help, a_flags)
EndFunction

Int Function AddNamedColor(String a_key, String a_text, Int a_color, String a_help = "", Int a_flags = 0)
	Return OpenMCM_AddNamed(a_key, OPTION_TYPE_COLOR, a_text, "", a_color, a_help, a_flags)
EndFunction

Int Function AddNamedKeyMap(String a_key, String a_text, Int a_keyCode, String a_help = "", Int a_flags = 0)
	Return OpenMCM_AddNamed(a_key, OPTION_TYPE_KEYMAP, a_text, "", a_keyCode, a_help, a_flags)
EndFunction

Int Function AddNamedInput(String a_key, String a_text, String a_value, String a_help = "", Int a_flags = 0)
	Return OpenMCM_AddNamed(a_key, OPTION_TYPE_INPUT, a_text, a_value, 0.0, a_help, a_flags)
EndFunction

; Retain SDK internal signatures for dependent compiled scripts, but do not
; intercept Bridge's ordinary HighlightOption or SetInfoText callback dispatch.
Int Function OpenMCM_CapturePageToken()
	Return 0
EndFunction

String Function OpenMCM_DefaultHelp(Int a_index)
	Return ""
EndFunction

Function OpenMCM_PublishHelp(Int a_index, String a_text, Int a_token)
EndFunction

Function OpenMCM_ClearPage()
	_openmcmPageToken = 0
	_openmcmHostToken = 0
	If _openmcmGeneration < 2147483647
		_openmcmGeneration += 1
	EndIf
	_openmcmProviderID = -1
	_openmcmPageIndex = -2
	_openmcmBuilding = False
	_openmcmKeys = New String[1]
	_openmcmHelp = New String[1]
	_openmcmIDs = New Int[1]
	_openmcmTypes = New Int[1]
	_openmcmBridgeStates = New String[1]
	_openmcmBridgeCursor = 0
	_openmcmBridgeFillMode = 1
EndFunction

Bool Function OpenMCM_CanBind(String a_key)
	If !_openmcmBuilding || _openmcmKeys == None || _openmcmKeys.Length != 128
		OpenMCM_Error("Bind/add '" + a_key + "' only during OnPageReset")
		Return False
	EndIf
	If a_key == ""
		OpenMCM_Error("Option keys cannot be empty")
		Return False
	EndIf
	If _openmcmKeys.Find(a_key) >= 0
		OpenMCM_Error("Duplicate option key '" + a_key + "'")
		Return False
	EndIf
	Return True
EndFunction

Int Function OpenMCM_ResolveID(Int a_option)
	If a_option < 0 || (a_option / 0x100) != (_openmcmPageIndex + 1)
		Return -1
	EndIf
	Int index = a_option % 0x100
	If index >= 128 || _openmcmIDs == None || _openmcmIDs.Length != 128
		Return -1
	EndIf
	If _openmcmIDs[index] != a_option || _openmcmTypes[index] == OPTION_TYPE_EMPTY
		Return -1
	EndIf
	Return index
EndFunction

Int Function OpenMCM_FindKey(String a_key)
	If a_key == "" || _openmcmKeys == None || _openmcmKeys.Length != 128
		OpenMCM_Error("No named option '" + a_key + "' on the current page")
		Return -1
	EndIf
	Int index = _openmcmKeys.Find(a_key)
	If index < 0
		OpenMCM_Error("Unknown option key '" + a_key + "'")
	EndIf
	Return index
EndFunction

Int Function OpenMCM_ResolveUpdate(String a_key, Int a_token)
	Return -1
EndFunction

Int Function OpenMCM_AddNamed(String a_key, Int a_type, String a_text, String a_value, Float a_number, String a_help, Int a_flags)
	If !OpenMCM_CanBind(a_key)
		Return -1
	EndIf
	Int optionID = AddOption(a_type, a_text, a_value, a_number, a_flags)
	If optionID < 0
		OpenMCM_Error("Could not add '" + a_key + "': no available or replaceable option slot")
		Return -1
	EndIf
	If !BindOption(a_key, optionID, a_help)
		Return -1
	EndIf
	Return optionID
EndFunction

Function OpenMCM_SendText(String a_method, Int a_option, String a_text, Int a_token)
	; Deliberate no-op: this adapter does not implement the extended host.
EndFunction

Function OpenMCM_Error(String a_message)
	Debug.Trace("OpenMCM basic MCM Bridge adapter [" + ModName + "/" + CurrentPage + "]: " + a_message)
EndFunction
