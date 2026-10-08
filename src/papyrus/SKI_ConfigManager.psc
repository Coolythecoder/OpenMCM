Scriptname SKI_ConfigManager extends SKI_QuestBase Hidden

; These strings are part of the MCM ABI. The Journal replacement must expose this exact path.
String Property JOURNAL_MENU = "Journal Menu" AutoReadOnly
String Property MENU_ROOT = "_root.ConfigPanelFader.configPanel" AutoReadOnly

; Keep the traditional field names and types. MCM Helper resolves several of these by name.
SKI_ConfigBase[] _modConfigs
String[] _modNames
Int _curConfigID = 0
Int _configCount = 0
SKI_ConfigBase _activeConfig

Bool _lockInit = False
Bool _locked = False
Bool _cleanupFlag = False
Int _addCounter = 0
Int _updateCounter = 0
; Appended for save compatibility. Existing saves initialize these to False.
Bool _storageRebuilt = False
Bool _menuOpen = False
Bool _registryBusy = False
; Save-local preference. Old saves and new games default to legacy-only use.
; Never reset this in reload/registry repair: each new movie is synchronized.
Bool _openmcmAPIEnabled = False
; Browser layout only: favourites, aliases, hidden names, sorting and tab state.
; Keep this separate from the registry and from provider settings. Names are
; the browser preference keys; no display edit changes a provider's ModName/ID.
String _openmcmBrowserState = ""

Int Function GetVersion()
	Return 4
EndFunction

Event OnInit()
	; Match SkyUI's initialization order exactly. The typed object registry must
	; exist before any provider receives SKICP_configManagerReady.
	_modConfigs = New SKI_ConfigBase[128]
	_modNames = New String[128]
	OnGameReload()
EndEvent

Event OnGameReload()
	_registryBusy = False
	GotoState("")
	_menuOpen = False
	InitializeStorage()

	RegisterForModEvent("SKICP_modSelected", "OnModSelect")
	RegisterForModEvent("SKICP_pageSelected", "OnPageSelect")
	RegisterForModEvent("SKICP_optionHighlighted", "OnOptionHighlight")
	RegisterForModEvent("SKICP_optionSelected", "OnOptionSelect")
	RegisterForModEvent("SKICP_optionDefaulted", "OnOptionDefault")
	RegisterForModEvent("SKICP_keymapChanged", "OnKeymapChange")
	RegisterForModEvent("SKICP_sliderSelected", "OnSliderSelect")
	RegisterForModEvent("SKICP_sliderAccepted", "OnSliderAccept")
	RegisterForModEvent("SKICP_menuSelected", "OnMenuSelect")
	RegisterForModEvent("SKICP_menuAccepted", "OnMenuAccept")
	RegisterForModEvent("SKICP_colorSelected", "OnColorSelect")
	RegisterForModEvent("SKICP_colorAccepted", "OnColorAccept")
	RegisterForModEvent("SKICP_inputSelected", "OnInputSelect")
	RegisterForModEvent("SKICP_inputAccepted", "OnInputAccept")
	RegisterForModEvent("SKICP_dialogCanceled", "OnDialogCancel")
	RegisterForModEvent("OPENMCM_modListRequested", "OnModListRequest")
	RegisterForModEvent("OPENMCM_browserStateChanged", "OnBrowserStateChanged")

	RegisterForMenu(JOURNAL_MENU)
	_lockInit = True
	_cleanupFlag = True
	CleanUp()
	If _storageRebuilt
		; A saved manager can retain names and counters after its typed object
		; array has been lost. Invalidate every menu's cached manager/slot before
		; announcing the repaired, empty registry.
		_storageRebuilt = False
		SendModEvent("SKICP_configManagerReset")
	EndIf
	SendModEvent("SKICP_configManagerReady")

	_updateCounter = 0
	RegisterForSingleUpdate(5.0)
EndEvent

Event OnUpdate()
	; Do not break a legitimate BUSY lock if the VM time-sliced a registry
	; mutation. Try again shortly after that non-latent operation completes.
	If _registryBusy
		RegisterForSingleUpdate(1.0)
		Return
	EndIf

	; Saves made while an older manager was BUSY can preserve that state even
	; though the Journal is no longer open. Recover before registration retries.
	If !_menuOpen
		GotoState("")
	EndIf

	InitializeStorage()
	If _storageRebuilt
		_storageRebuilt = False
		_updateCounter = 0
		SendModEvent("SKICP_configManagerReset")
	EndIf

	If _cleanupFlag
		CleanUp()
	EndIf

	If _addCounter > 0
		Debug.Notification("MCM: Registered " + _addCounter + " new menu(s).")
		_addCounter = 0
	EndIf

	; Repeating this signal closes the load-order race with menus initialized after the manager.
	SendModEvent("SKICP_configManagerReady")
	If _updateCounter < 6
		_updateCounter += 1
		RegisterForSingleUpdate(5.0)
	Else
		RegisterForSingleUpdate(30.0)
	EndIf
EndEvent

Event OnMenuOpen(String a_menuName)
	_menuOpen = True
	GotoState("BUSY")
	_activeConfig = None
	; Match SkyUI's single initial publication. If this precedes dynamic panel
	; attachment, startPage requests the list through the existing selection
	; event and stops retrying as soon as setModNames acknowledges it.
	PublishModList()
EndEvent

; OpenMCM installs its ConfigPanel dynamically while the Journal is loading.
; If the normal OnMenuOpen push races that installation, the fully initialized
; panel requests another copy when the user actually opens the MCM page.
Event OnModListRequest(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	PublishModList()
EndEvent

Event OnBrowserStateChanged(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	; The panel validates its complete format before sending. Check the envelope
	; again at the save boundary and keep the last good snapshot on bad input.
	; Do not require an open Journal here: a final explicit edit can reach this
	; queued event just after the movie closes. This handler never invokes UI.
	If !IsValidBrowserState(a_strArg)
		Return
	EndIf
	_openmcmBrowserState = a_strArg
EndEvent

Event OnMenuClose(String a_menuName)
	_menuOpen = False
	GotoState("")
	If _activeConfig != None
		_activeConfig.CloseConfig()
	EndIf
	_activeConfig = None
	; Pending registrations retry on the normal SkyUI readiness heartbeat.
EndEvent

Event OnModSelect(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	Int index = a_numArg as Int
	; -1 is OpenMCM's saved-game-safe list refresh sentinel. Every existing
	; SkyUI-compatible save already has SKICP_modSelected registered, whereas a
	; newly added custom event registration is not guaranteed to enter a co-save
	; merely because its PEX was upgraded.
	If index < 0
		PublishModList()
		Return
	EndIf
	If IsRegisteredIndex(index)
		If _activeConfig != None
			_activeConfig.CloseConfig()
		EndIf
		_activeConfig = _modConfigs[index]
		_activeConfig.OpenConfig()
	EndIf
	UnlockPanel()
EndEvent

Event OnPageSelect(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.SetPage(a_strArg, a_numArg as Int)
	EndIf
	UnlockPanel()
EndEvent

Event OnOptionHighlight(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.HighlightOption(a_numArg as Int)
	EndIf
EndEvent

Event OnOptionSelect(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.SelectOption(a_numArg as Int)
	EndIf
	UnlockPanel()
EndEvent

Event OnOptionDefault(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.ResetOption(a_numArg as Int)
	EndIf
	UnlockPanel()
EndEvent

Event OnKeymapChange(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig == None
		UnlockPanel()
		Return
	EndIf

	Int optionIndex = a_numArg as Int
	Int keyCode = UI.GetInt(JOURNAL_MENU, MENU_ROOT + ".selectedKeyCode")
	String conflictControl = Input.GetMappedControl(keyCode)
	String conflictName = ""

	Int i = 0
	While conflictControl == "" && i < 128
		If _modConfigs[i] != None
			conflictControl = _modConfigs[i].GetCustomControl(keyCode)
			If conflictControl != ""
				conflictName = _modNames[i]
			EndIf
		EndIf
		i += 1
	EndWhile

	_activeConfig.RemapKey(optionIndex, keyCode, conflictControl, conflictName)
	UnlockPanel()
EndEvent

Event OnSliderSelect(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.RequestSliderDialogData(a_numArg as Int)
	Else
		UnlockPanel()
	EndIf
EndEvent

Event OnSliderAccept(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.SetSliderValue(a_numArg)
	EndIf
	UnlockPanel()
EndEvent

Event OnMenuSelect(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.RequestMenuDialogData(a_numArg as Int)
	Else
		UnlockPanel()
	EndIf
EndEvent

Event OnMenuAccept(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.SetMenuIndex(a_numArg as Int)
	EndIf
	UnlockPanel()
EndEvent

Event OnColorSelect(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.RequestColorDialogData(a_numArg as Int)
	Else
		UnlockPanel()
	EndIf
EndEvent

Event OnColorAccept(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.SetColorValue(a_numArg as Int)
	EndIf
	UnlockPanel()
EndEvent

Event OnInputSelect(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.RequestInputDialogData(a_numArg as Int)
	Else
		UnlockPanel()
	EndIf
EndEvent

Event OnInputAccept(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If _activeConfig != None
		_activeConfig.SetInputText(a_strArg)
	EndIf
	UnlockPanel()
EndEvent

Event OnDialogCancel(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	UnlockPanel()
EndEvent

Int Function RegisterMod(SKI_ConfigBase a_menu, String a_modName)
	If a_menu == None
		Return -1
	EndIf
	If _registryBusy
		Return -2
	EndIf

	_registryBusy = True
	GotoState("BUSY")
	InitializeStorage()
	If !HasValidStorage()
		Debug.Trace(Self + ": refusing MCM registration because registry storage is unavailable")
		_registryBusy = False
		GotoState("")
		Return -1
	EndIf

	; Keep the original RegisterMod ABI and verify saved client identities on
	; every retry. Native Find avoids a Papyrus loop over 128 slots per provider
	; without trusting stale client caches or requiring a new manager method.
	Int existingID = _modConfigs.Find(a_menu)
	If existingID >= 0
		_modNames[existingID] = a_modName
		_registryBusy = False
		GotoState("")
		; A repeated registration must neither republish nor notify.
		Return existingID
	EndIf

	If _configCount >= 128
		_registryBusy = False
		GotoState("")
		Return -1
	EndIf

	Int newID = NextID()
	If newID < 0
		_registryBusy = False
		GotoState("")
		Return -1
	EndIf

	_modConfigs[newID] = a_menu
	_modNames[newID] = a_modName
	If _modConfigs[newID] != a_menu
		Debug.Trace(Self + ": MCM registration write did not persist for " + a_modName)
		_registryBusy = False
		GotoState("")
		Return -1
	EndIf
	_configCount += 1
	_addCounter += 1
	_registryBusy = False
	GotoState("")
	PublishModList()
	Return newID
EndFunction

Int Function UnregisterMod(SKI_ConfigBase a_menu)
	If a_menu == None
		Return -1
	EndIf
	If _registryBusy
		Return -2
	EndIf
	_registryBusy = True
	GotoState("BUSY")
	InitializeStorage()
	If !HasValidStorage()
		_registryBusy = False
		GotoState("")
		Return -1
	EndIf
	Int existingID = _modConfigs.Find(a_menu)
	If existingID >= 0
		_modConfigs[existingID] = None
		_modNames[existingID] = ""
		If _configCount > 0
			_configCount -= 1
		EndIf
		_curConfigID = existingID
		_registryBusy = False
		GotoState("")
		PublishModList()
		Return existingID
	EndIf
	_registryBusy = False
	GotoState("")
	Return -1
EndFunction

Function ForceReset()
	; Preserve the SkyUI API 4 entry point. Callers needing an acknowledgement
	; use the OpenMCM extension below; a quest stage result is not reset success.
	OpenMCM_TryForceReset()
EndFunction

Bool Function OpenMCM_TryForceReset()
	; Menu events may still be queued in the VM. Check actual visibility too,
	; without changing state or scheduling a reset on a rejected request.
	If UI.IsMenuOpen(JOURNAL_MENU) || UI.IsMenuOpen("RaceSex Menu")
		Return False
	EndIf
	; Do native calls before admission: their execution can yield to a queued
	; menu event or registry mutation. Check local locks last with no external
	; call between the guard and acquiring this reset's registry lock.
	If _menuOpen
		Return False
	EndIf
	If _registryBusy
		Return False
	EndIf
	_registryBusy = True
	GotoState("BUSY")
	InitializeStorage()
	If !HasValidStorage()
		_registryBusy = False
		GotoState("")
		Return False
	EndIf
	Debug.Trace(Self + ": forcing MCM registry reset")

	Int i = 0
	While i < 128
		_modConfigs[i] = None
		_modNames[i] = ""
		i += 1
	EndWhile

	_activeConfig = None
	_curConfigID = 0
	_configCount = 0
	_addCounter = 0
	_storageRebuilt = False
	; Do not invalidate provider identities until storage validation and the
	; reset mutation have completed. Success acknowledges this reset only,
	; not completion of asynchronous provider registration callbacks.
	SendModEvent("SKICP_configManagerReset")
	_registryBusy = False
	GotoState("")
	PublishModList()
	SendModEvent("SKICP_configManagerReady")
	Return True
EndFunction

Function CleanUp()
	If _registryBusy
		Return
	EndIf
	_registryBusy = True
	GotoState("BUSY")
	InitializeStorage()
	If !HasValidStorage()
		_registryBusy = False
		GotoState("")
		Return
	EndIf
	_cleanupFlag = False
	_configCount = 0

	Int i = 0
	While i < 128
		If _modConfigs[i] == None
			_modNames[i] = ""
		ElseIf _modConfigs[i].GetFormID() == 0
			_modConfigs[i] = None
			_modNames[i] = ""
		Else
			; Names are a display cache. Keep them derived from the authoritative
			; menu object array so a partially damaged save repairs cleanly.
			_modNames[i] = _modConfigs[i].ModName
			_configCount += 1
		EndIf
		i += 1
	EndWhile
	_registryBusy = False
	GotoState("")
EndFunction

Int Function NextID()
	If !HasValidStorage()
		Return -1
	EndIf
	; Preserve circular allocation and sparse registry IDs using native lookups.
	Int next = _modConfigs.Find(None, _curConfigID)
	If next < 0
		next = _modConfigs.Find(None)
	EndIf
	If next >= 0
		_curConfigID = next
	EndIf
	Return next
EndFunction

Function InitializeStorage()
	Bool rebuildObjects = False
	If _modConfigs == None
		rebuildObjects = True
	ElseIf _modConfigs.Length != 128
		rebuildObjects = True
	EndIf

	If rebuildObjects
		_modConfigs = New SKI_ConfigBase[128]
		_modNames = New String[128]
		_configCount = 0
		_curConfigID = 0
		_addCounter = 0
		_activeConfig = None
		_storageRebuilt = True
		Debug.Trace(Self + ": rebuilt missing MCM object registry")
	Else
		If _curConfigID < 0 || _curConfigID >= 128
			_curConfigID = 0
		EndIf
		Bool rebuildNames = False
		If _modNames == None
			rebuildNames = True
		ElseIf _modNames.Length != 128
			rebuildNames = True
		EndIf

		If !rebuildNames
			Return
		EndIf

		_modNames = New String[128]
		Int i = 0
		While i < 128
			If _modConfigs[i] != None
				_modNames[i] = _modConfigs[i].ModName
			EndIf
			i += 1
		EndWhile
	EndIf
EndFunction

Bool Function HasValidStorage()
	If _modConfigs == None
		Return False
	EndIf
	If _modConfigs.Length != 128
		Return False
	EndIf
	If _modNames == None
		Return False
	EndIf
	If _modNames.Length != 128
		Return False
	EndIf
	Return True
EndFunction

Bool Function IsRegisteredIndex(Int a_index)
	If a_index < 0 || a_index >= 128
		Return False
	EndIf
	If !HasValidStorage()
		Return False
	EndIf
	Return _modConfigs[a_index] != None
EndFunction

; A menu's cached manager and slot survive in its script instance even when the
; manager's parallel registry array does not. Match the exact pair used by MCM
; Helper's HasConfig invariant; RegisterMod's dedupe scan repairs a stale slot.
Bool Function IsRegisteredMod(SKI_ConfigBase a_menu, Int a_expectedID = -1)
	If a_menu == None
		Return False
	EndIf
	InitializeStorage()
	If !HasValidStorage()
		Return False
	EndIf
	If a_expectedID < 0 || a_expectedID >= 128
		Return False
	EndIf
	Return _modConfigs[a_expectedID] == a_menu
EndFunction

Function PublishModList()
	; Registration and repair also run during gameplay/character creation. Do
	; not queue a Scaleform invocation or build a display cache for a closed
	; Journal. Its open event and the panel's request/ack handshake fetch the
	; authoritative list when it is actually needed.
	If !UI.IsMenuOpen(JOURNAL_MENU)
		Return
	EndIf
	InitializeStorage()
	If !HasValidStorage()
		Debug.Trace(Self + ": cannot publish MCM list because registry storage is unavailable")
		Return
	EndIf
	; The panel can be attached after OnMenuOpen. Its request/ack path must
	; restore the preference before exposing providers, not only on first open.
	PublishOpenMCMAPIState()
	PublishBrowserState()
	UI.InvokeStringA(JOURNAL_MENU, MENU_ROOT + ".setModNames", _modNames)
EndFunction

Bool Function IsValidBrowserState(String a_state)
	Int stateLength = StringUtil.GetLength(a_state)
	If stateLength < 10 || stateLength > 32768
		Return False
	EndIf
	Return StringUtil.Substring(a_state, 0, 10) == "OPENMCMB1|"
EndFunction

Function PublishBrowserState()
	If !UI.IsMenuOpen(JOURNAL_MENU)
		Return
	EndIf
	; Empty means a fresh/old save without browser preferences. The movie owns
	; parsing and falls back to defaults. A valid native global profile, when
	; available, takes precedence without modifying this save-local snapshot.
	UI.InvokeString(JOURNAL_MENU, MENU_ROOT + ".loadBrowserState", _openmcmBrowserState)
EndFunction

Bool Function IsOpenMCMAPIEnabled()
	Return _openmcmAPIEnabled
EndFunction

Function SetOpenMCMAPIEnabled(Bool a_enabled)
	_openmcmAPIEnabled = a_enabled
	PublishOpenMCMAPIState()
EndFunction

Function PublishOpenMCMAPIState()
	If !UI.IsMenuOpen(JOURNAL_MENU)
		Return
	EndIf
	UI.InvokeBool(JOURNAL_MENU, MENU_ROOT + ".setOpenMCMAPIEnabled", _openmcmAPIEnabled)
EndFunction

Function UnlockPanel()
	UI.InvokeBool(JOURNAL_MENU, MENU_ROOT + ".unlock", True)
EndFunction

Function Log(String a_msg)
	Debug.Trace(Self + ": " + a_msg)
EndFunction

State BUSY
	Int Function RegisterMod(SKI_ConfigBase a_menu, String a_modName)
		Return -2
	EndFunction

	Int Function UnregisterMod(SKI_ConfigBase a_menu)
		Return -2
	EndFunction

	Function ForceReset()
	EndFunction

	Bool Function OpenMCM_TryForceReset()
		Return False
	EndFunction

	Function CleanUp()
	EndFunction
EndState
