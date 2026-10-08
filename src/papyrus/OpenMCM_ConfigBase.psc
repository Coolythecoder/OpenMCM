Scriptname OpenMCM_ConfigBase extends SKI_ConfigBase

; Opt-in API 1. Legacy SkyUI/MCM Helper providers need no changes.
; All saved fields have a separate prefix: never shadow SkyUI's ABI fields.
String[] _openmcmKeys
String[] _openmcmHelp
Int[] _openmcmIDs
Int[] _openmcmTypes
Int _openmcmPageIndex = -2
Int _openmcmProviderID = -1
Int _openmcmPageToken = 0
Int _openmcmHostToken = 0
; Persist across close/reopen: an entirely new Journal can reuse its UI token.
Int _openmcmGeneration = 0
Bool _openmcmBuilding = False

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
	_openmcmKeys = New String[128]
	_openmcmHelp = New String[128]
	_openmcmIDs = New Int[128]
	_openmcmTypes = New Int[128]
	_openmcmPageIndex = a_index
	_openmcmBuilding = True
	Parent.SetPage(a_page, a_index)
	_openmcmBuilding = False
	_openmcmProviderID = OpenMCM_GetConfigID()
	; The host publishes a fresh token when it flushes this page's buffers.
	; Never obtain a replacement token while completing an old async action.
	If _openmcmGeneration < 2147483647 && _openmcmProviderID >= 0 && UI.GetInt(JOURNAL_MENU, MENU_ROOT + ".openMCMProviderID") == _openmcmProviderID && UI.GetInt(JOURNAL_MENU, MENU_ROOT + ".openMCMPageIndex") == a_index
		_openmcmHostToken = UI.GetInt(JOURNAL_MENU, MENU_ROOT + ".openMCMPageToken")
		If _openmcmHostToken > 0
			_openmcmPageToken = _openmcmGeneration
		EndIf
	EndIf
EndFunction

; Track ordinary and ST additions too. Rewinding the cursor and replacing a
; row must remove its old binding/help, even when the replacement is unnamed.
Int Function AddOption(Int a_optionType, String a_text, String a_strValue, Float a_numValue, Int a_flags)
	Int optionID = Parent.AddOption(a_optionType, a_text, a_strValue, a_numValue, a_flags)
	If optionID >= 0 && _openmcmBuilding
		Int index = optionID % 0x100
		OpenMCM_ClearOptionState(optionID)
		_openmcmKeys[index] = ""
		_openmcmHelp[index] = ""
		_openmcmIDs[index] = optionID
		_openmcmTypes[index] = a_optionType
	EndIf
	Return optionID
EndFunction

; Bind existing Add*Option results, including headers. Bindings are per page,
; recreated in OnPageReset, and never change the numeric callback IDs.
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

; Capture at the START of a callback, before waits/work. Zero means no ready
; page. Passing a fresh token at the END of old work is not safe.
Int Function GetPageToken()
	If IsPageTokenValid(_openmcmPageToken)
		Return _openmcmPageToken
	EndIf
	Return 0
EndFunction

Bool Function IsPageTokenValid(Int a_token)
	If !UI.GetBool(JOURNAL_MENU, MENU_ROOT + ".openMCMApiEnabled")
		Return False
	EndIf
	Return OpenMCM_IsPageContextValid(a_token)
EndFunction

; Internal scope is also needed by explicit legacy highlight callbacks when
; optional features are off. Public async tokens remain unavailable then.
Bool Function OpenMCM_IsPageContextValid(Int a_token)
	If a_token <= 0 || a_token != _openmcmPageToken || _openmcmBuilding || _openmcmProviderID < 0
		Return False
	EndIf
	If UI.GetInt(JOURNAL_MENU, MENU_ROOT + ".openMCMProviderID") != _openmcmProviderID || UI.GetInt(JOURNAL_MENU, MENU_ROOT + ".openMCMPageIndex") != _openmcmPageIndex
		Return False
	EndIf
	Bool hostMatches = UI.GetInt(JOURNAL_MENU, MENU_ROOT + ".openMCMPageToken") == _openmcmHostToken
	Return hostMatches && a_token == _openmcmPageToken && !_openmcmBuilding
EndFunction

; These update presentation, not the mod's own settings. Keep your setting
; variables in sync and use them when rebuilding a page. True means queued;
; the host rechecks ownership when applying the complete atomic payload.
Bool Function SetOptionLabel(String a_key, String a_text, Int a_token)
	Int index = OpenMCM_ResolveUpdate(a_key, a_token)
	If index < 0
		Return False
	EndIf
	OpenMCM_SendText("openMCMSetOptionLabel", _openmcmIDs[index], a_text, a_token)
	Return True
EndFunction

Bool Function SetOptionText(String a_key, String a_text, Int a_token)
	Int index = OpenMCM_ResolveUpdate(a_key, a_token)
	If index < 0
		Return False
	EndIf
	If _openmcmTypes[index] != OPTION_TYPE_TEXT
		OpenMCM_Error("'" + a_key + "' is not a text option; use its SkyUI typed value setter")
		Return False
	EndIf
	OpenMCM_SendText("openMCMSetOptionTextValue", _openmcmIDs[index], a_text, a_token)
	Return True
EndFunction

Bool Function SetOptionHelp(String a_key, String a_text, Int a_token)
	; A UI getter can yield. Keep an old stack from writing into a replacement
	; page's newly allocated help array if the user leaves during validation.
	String[] targetHelp = _openmcmHelp
	Int index = OpenMCM_ResolveUpdate(a_key, a_token)
	If index < 0
		Return False
	EndIf
	If targetHelp == None || targetHelp.Length != 128 || a_token != _openmcmPageToken
		Return False
	EndIf
	targetHelp[index] = a_text
	; Only replaces the footer immediately if this option is still highlighted.
	OpenMCM_SendText("openMCMSetInfoText", _openmcmIDs[index], a_text, a_token)
	Return True
EndFunction

Bool Function SetLiveInfoText(String a_text, Int a_token)
	If !IsPageTokenValid(a_token)
		OpenMCM_Error("Live help rejected: inactive page or stale token " + a_token)
		Return False
	EndIf
	OpenMCM_SendText("openMCMSetInfoText", -1, a_text, a_token)
	Return True
EndFunction

; Navigate only within this provider's published Pages. The host queues the
; request until the current selection callback unlocks; never call SetPage
; directly, which would desynchronize its sidebar and option ID namespace.
Bool Function SetCurrentPage(String a_page, Int a_token)
	If !IsPageTokenValid(a_token) || Pages == None || a_page == "" || a_page == "None"
		Return False
	EndIf
	Int destination = Pages.Find(a_page)
	If destination < 0
		Return False
	EndIf
	OpenMCM_SendText("openMCMRequestPage", destination, a_page, a_token)
	Return a_token == _openmcmPageToken && !_openmcmBuilding
EndFunction

; Conditional groups: change only the DISABLED bit, retaining hidden/unmap
; flags. Validation is all-or-nothing and the host paints the group once.
; This is live presentation, not persistent setting storage: rebuild flags
; from your own condition in OnPageReset, as with other live SDK updates.
Bool Function SetOptionsEnabled(String[] a_keys, Bool a_enabled, Int a_token)
	If !IsPageTokenValid(a_token) || a_keys == None || a_keys.Length == 0 || a_keys.Length > 128
		Return False
	EndIf
	String ids = ""
	Int i = 0
	While i < a_keys.Length
		Int index = OpenMCM_FindKey(a_keys[i])
		If index < 0 || a_token != _openmcmPageToken || _openmcmBuilding
			Return False
		EndIf
		If i > 0
			ids += ","
		EndIf
		ids += _openmcmIDs[index] as String
		i += 1
	EndWhile
	OpenMCM_SendText("openMCMSetOptionsEnabled", a_enabled as Int, ids, a_token)
	Return a_token == _openmcmPageToken && !_openmcmBuilding
EndFunction

; Convenience additions retain exactly the standard SkyUI option types.
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

; Bridge hooks called by the unchanged normal/ST highlight dispatch. Default
; help is installed BEFORE the callback, so SetInfoText("") can clear it too.
Int Function OpenMCM_CapturePageToken()
	If OpenMCM_IsPageContextValid(_openmcmPageToken)
		Return _openmcmPageToken
	EndIf
	Return 0
EndFunction

String Function OpenMCM_DefaultHelp(Int a_index)
	If !UI.GetBool(JOURNAL_MENU, MENU_ROOT + ".openMCMApiEnabled")
		Return ""
	EndIf
	If a_index >= 0 && a_index < 128 && _openmcmHelp != None && _openmcmHelp.Length == 128
		Return _openmcmHelp[a_index]
	EndIf
	Return ""
EndFunction

Function OpenMCM_PublishHelp(Int a_index, String a_text, Int a_token)
	If !OpenMCM_IsPageContextValid(a_token)
		Return
	EndIf
	; -2 clears help only if the UI still has no highlighted option. -1 is
	; reserved for explicit page status, independent of highlighted row.
	Int optionID = -2
	If a_index >= 0 && a_index < 128
		optionID = _openmcmIDs[a_index]
	EndIf
	; Unlike optional live status, normal OnOptionHighlight/OnHighlightST help
	; must work while the user disables extensions. The host still checks scope.
	OpenMCM_SendText("openMCMSetHighlightText", optionID, a_text, a_token)
EndFunction

; Internal SDK implementation -------------------------------------------------
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
EndFunction

Bool Function OpenMCM_CanBind(String a_key)
	If !_openmcmBuilding
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
	If !IsPageTokenValid(a_token)
		OpenMCM_Error("Update '" + a_key + "' rejected: inactive page or stale token " + a_token)
		Return -1
	EndIf
	Return OpenMCM_FindKey(a_key)
EndFunction

Int Function OpenMCM_AddNamed(String a_key, Int a_type, String a_text, String a_value, Float a_number, String a_help, Int a_flags)
	If !OpenMCM_CanBind(a_key)
		Return -1
	EndIf
	Int optionID = AddOption(a_type, a_text, a_value, a_number, a_flags)
	If optionID < 0
		OpenMCM_Error("Could not add '" + a_key + "': no available option slot (128 per page)")
		Return -1
	EndIf
	If !BindOption(a_key, optionID, a_help)
		Return -1
	EndIf
	Return optionID
EndFunction

Function OpenMCM_SendText(String a_method, Int a_option, String a_text, Int a_token)
	If a_token <= 0 || a_token != _openmcmPageToken || _openmcmHostToken <= 0
		Return
	EndIf
	String[] params = New String[5]
	params[0] = _openmcmProviderID as String
	params[1] = _openmcmPageIndex as String
	params[2] = _openmcmHostToken as String
	params[3] = a_option as String
	params[4] = a_text
	UI.InvokeStringA(JOURNAL_MENU, MENU_ROOT + "." + a_method, params)
EndFunction

Function OpenMCM_Error(String a_message)
	Debug.Trace("OpenMCM API 1 [" + ModName + "/" + CurrentPage + "]: " + a_message)
EndFunction
