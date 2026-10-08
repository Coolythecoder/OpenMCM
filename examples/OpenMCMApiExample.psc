Scriptname OpenMCMApiExample extends OpenMCM_ConfigBase

; SDK example only; no quest is installed automatically. Attach this script to
; a start-game-enabled quest as described in docs/OpenMCM-API.md.
Bool featureEnabled = True
Int runCount = 0
Bool running = False
Int pendingToken = 0

Event OnGameReload()
	Parent.OnGameReload()
	running = False
	pendingToken = 0
	RegisterForModEvent("OpenMCMApiExample_Run", "OnExampleRun")
EndEvent

Event OnConfigInit()
	ModName = "OpenMCM API Example"
	Pages = New String[2]
	Pages[0] = "Live updates"
	Pages[1] = "State callbacks"
EndEvent

Event OnPageReset(String a_page)
	SetCursorFillMode(TOP_TO_BOTTOM)
	Int apiFlags = OPTION_FLAG_NONE
	If !OpenMCM.IsAPIEnabled()
		apiFlags = OPTION_FLAG_DISABLED
		AddHeaderOption("Enable API in OpenMCM > Status > Runtime")
	EndIf
	Int actionFlags = apiFlags
	If !featureEnabled
		actionFlags = OPTION_FLAG_DISABLED
	EndIf
	If a_page == "State callbacks"
		AddTextOptionST("RunState", "Run state-based action", "Select", actionFlags)
		BindStateOption("run_state", "RunState", "This automatic help also works with SkyUI state callbacks.")
		AddNamedText("status", "Last result", "Runs: " + runCount, "A presentation-only status value.", OPTION_FLAG_DISABLED)
		AddNamedText("go_live", "Go to live updates", "Open", "Navigate through the provider's published Pages safely.", apiFlags)
	Else
		AddNamedHeader("heading", "OpenMCM API 1")
		AddNamedToggle("enabled", "Enable example", featureEnabled, "Automatic help: no highlight callback required.")
		AddNamedText("run", "Run example action", "Select", "Updates the label, value and footer without rebuilding the page.", actionFlags)
		AddNamedText("reset_count", "Reset completed actions", "Reset", "Enabled together with Run example action as a conditional group.", actionFlags)
		AddNamedText("status", "Last result", "Runs: " + runCount, "Updated after the action finishes.", OPTION_FLAG_DISABLED)
		AddNamedText("go_states", "Go to state callbacks", "Open", "The host defers navigation until this callback completes.", apiFlags)
	EndIf
EndEvent

Event OnOptionSelect(Int a_option)
	; Capture BEFORE work. Do not call GetPageToken again after waiting.
	Int pageToken = GetPageToken()
	If CurrentPage == "State callbacks"
		If a_option == GetOptionID("go_live")
			SetCurrentPage("Live updates", pageToken)
		EndIf
		Return
	EndIf
	If a_option == GetOptionID("enabled")
		featureEnabled = !featureEnabled
		; Existing SkyUI typed value setters and numeric callbacks still work.
		SetToggleOptionValue(a_option, featureEnabled)
		String[] actions = New String[2]
		actions[0] = "run"
		actions[1] = "reset_count"
		; Group changes preserve hidden/unmap flags and paint only once. The
		; same condition above also rebuilds the correct flags after reopening.
		If !SetOptionsEnabled(actions, featureEnabled, pageToken)
			ForcePageReset()
		EndIf
	ElseIf a_option == GetOptionID("run")
		RunExample(pageToken)
	ElseIf a_option == GetOptionID("reset_count")
		runCount = 0
		SetOptionText("status", "Runs: 0", pageToken)
	ElseIf a_option == GetOptionID("go_states")
		SetCurrentPage("State callbacks", pageToken)
	EndIf
EndEvent

Event OnOptionHighlight(Int a_option)
	If CurrentPage != "State callbacks" && a_option == GetOptionID("run") && running
		; Explicit callback text overrides the automatic help. An empty string
		; explicitly clears it; it does not restore the default.
		SetInfoText("The example action is already running.")
	EndIf
EndEvent

Function RunExample(Int a_pageToken)
	If running || !featureEnabled || !IsPageTokenValid(a_pageToken)
		Return
	EndIf
	running = True
	pendingToken = a_pageToken
	; Return from the selection callback so SkyUI's manager can unlock input.
	; Only this example schedules work; the SDK itself adds no worker/polling.
	SendModEvent("OpenMCMApiExample_Run")
EndFunction

Event OnExampleRun(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	If a_sender != Self || !running
		Return
	EndIf
	Int pageToken = pendingToken
	SetLiveInfoText("Working: you can change pages while this example waits.", pageToken)
	Utility.WaitMenuMode(0.5)
	runCount += 1
	running = False
	; Keep the stored state even if the page changed. Suppress obsolete UI work.
	If !IsPageTokenValid(pageToken)
		Return
	EndIf
	SetOptionLabel("status", "<font color='#80D0FF'>Completed actions</font>", pageToken)
	SetOptionText("status", "Runs: " + runCount, pageToken)
	SetOptionHelp("status", "This text was updated after the action finished.", pageToken)
	SetLiveInfoText("Complete. No page reset was needed.", pageToken)
EndEvent

State RunState
	Event OnSelectST()
		Int pageToken = GetPageToken()
		RunExample(pageToken)
	EndEvent

	Event OnHighlightST()
		If running
			SetInfoText("The state-based action is already running.")
		EndIf
	EndEvent
EndState
