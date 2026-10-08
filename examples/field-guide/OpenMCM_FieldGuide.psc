Scriptname OpenMCM_FieldGuide extends OpenMCM_ConfigBase

; OPENMCM FIELD GUIDE 1.0.0 — a runnable, read-only trip planner.
; Author walkthrough: README.md beside this file.
; These variables belong to this mod and are saved with its quest/savegame.
; API setters change presentation, not these values or the player's inventory.
Bool guideEnabled = True
String tripName = "Next adventure"
Float weightBudget = 200.0
Int travelStyle = 0
Int accentColor = 0x80D0FF
Int summaryKey = -1 ; Unbound: no global key listener until the player opts in.
Bool suppliesReady = False
Bool equipmentReady = False
Bool routeReady = False
String[] styleNames

; A fresh, explicitly requested snapshot, not a continuously polled HUD.
Float carriedWeight = 0.0
Float carryCapacity = 0.0
Bool playerAvailable = False
Bool refreshPending = False
Int refreshGeneration = 0
Int pendingPageToken = 0

; 1. Lifecycle: retain your mod version; never replace it with the SDK version.
Int Function GetVersion()
	Return 1
EndFunction

Event OnConfigInit()
	ModName = "OpenMCM Field Guide"
	Pages = New String[3]
	Pages[0] = "Overview"
	Pages[1] = "Checklist"
	Pages[2] = "Preferences"
	EnsureStyleNames()
EndEvent

Event OnGameReload()
	CancelPendingRefresh()
	Parent.OnGameReload() ; Required: invalidates SDK scope and restores registration.
	EnsureStyleNames()
	RegisterForModEvent("OpenMCM_FieldGuide_Refresh", "OnDelayedRefresh")
	RebindSummaryKey()
EndEvent

Event OnConfigClose()
	CancelPendingRefresh() ; No delayed job may outlive this open configuration.
EndEvent

Function EnsureStyleNames()
	If styleNames == None || styleNames.Length != 3
		styleNames = New String[3]
		styleNames[0] = "Day trip"
		styleNames[1] = "Dungeon delve"
		styleNames[2] = "Long expedition"
	EndIf
EndFunction

; 2. Build named controls normally. Never capture a page token in OnPageReset:
; the host has not published the new page until this callback returns.
Event OnPageReset(String a_page)
	EnsureStyleNames()
	ReadLoad()
	SetCursorFillMode(TOP_TO_BOTTOM)
	SetTitleText("Field Guide")
	AddNamedHeader("heading", "OpenMCM Field Guide")
	AddNamedToggle("enabled", "Enable field guide", guideEnabled, "Enables checklist actions and the optional summary hotkey. Changes no gameplay values.")
	If !OpenMCM.IsAPIEnabled()
		AddHeaderOption("API extensions off — normal controls still work")
	EndIf

	If a_page == "Checklist"
		AddNamedHeader("checks_heading", "Manual preparation checklist")
		AddNamedToggle("supplies", "Supplies packed", suppliesReady, "Your manual reminder; this does not inspect or consume food, potions or arrows.", FeatureFlags())
		AddNamedToggle("equipment", "Equipment checked", equipmentReady, "Mark armour and weapons ready. No equipment is changed.", FeatureFlags())
		AddNamedToggle("route", "Route chosen", routeReady, "Remember whether you have planned your route. No quest or map marker is modified.", FeatureFlags())
		AddNamedText("check_summary", "Preparation", ChecklistText(), "Rebuilt from saved booleans whenever this page opens.", OPTION_FLAG_DISABLED)
		; ST callbacks still work. Bind after creating the existing SkyUI control.
		AddTextOptionST("ResetChecklist", "Clear checklist", "Reset", FeatureFlags())
		BindStateOption("clear_checks", "ResetChecklist", "Confirm before clearing the three manual checkmarks. Other preferences are retained.")
		SetCursorPosition(1)
		AddNamedHeader("notes_heading", "Plan")
		AddNamedText("trip", "Trip", EscapeLabelText(tripName), "Change the trip name on Preferences.", OPTION_FLAG_DISABLED)
		AddNamedText("style", "Travel style", styleNames[travelStyle], "A planning label, not a gameplay preset.", OPTION_FLAG_DISABLED)
		AddNamedText("go_overview", "View load summary", "Open", "API 1 navigation runs after this callback unlocks. Sidebar navigation always works.", APIFlags())
	ElseIf a_page == "Preferences"
		AddNamedHeader("plan_heading", "Trip preferences")
		AddNamedInput("trip_name", "Trip name", EscapeLabelText(tripName), "Up to 40 characters, saved with this character. Empty input restores Next adventure.")
		AddNamedMenu("travel_style", "Travel style", styleNames[travelStyle], "Labels this trip as a day trip, dungeon delve or long expedition; it does not apply gameplay settings.")
		AddNamedSlider("budget", "Planned carry budget", weightBudget, "{0}", "Planning target from 25 to 500 weight units. Does not change the player's actual carry capacity.")
		AddNamedColor("accent", "Summary heading colour", accentColor, "Applies an explicit HTML colour to the load heading. Inspect AccentHeading for the conversion.")
		AddNamedKeyMap("summary_key", "Summary hotkey (optional)", summaryKey, "Unbound by default. Keyboard only; shows a notification outside menus. Disable the guide to stop listening.", OPTION_FLAG_WITH_UNMAP)
		SetCursorPosition(1)
		AddNamedHeader("api_heading", "About the extension")
		AddNamedText("api_version", "Installed API", "Version " + OpenMCM.GetAPIVersion(), "SDK capability/version detection does not mean that the player enabled it.", OPTION_FLAG_DISABLED)
		AddNamedText("api_enabled", "Runtime API switch", APIStatus(), "Enable it in OpenMCM > Status > Runtime. This sample never enables it for you.", OPTION_FLAG_DISABLED)
		AddNamedText("go_overview", "View load summary", "Open", "Requires the Runtime API switch. Otherwise select Overview in the sidebar.", APIFlags())
	Else
		; SkyUI first opens the empty page name. Treat it as Overview as well.
		AddNamedText("trip", "Trip", EscapeLabelText(tripName), "Rename the trip on Preferences.", OPTION_FLAG_DISABLED)
		AddNamedText("style", "Travel style", styleNames[travelStyle], "Your planning label; it does not apply gameplay effects.", OPTION_FLAG_DISABLED)
		AddNamedHeader("load_heading", AccentHeading())
		AddNamedText("load", "Carried / capacity", LoadText(), "Reads InventoryWeight and CarryWeight from the player only when requested.", OPTION_FLAG_DISABLED)
		AddNamedText("budget_status", "Planned budget", BudgetText(), "Your target is independent of the player's actual carry capacity.", OPTION_FLAG_DISABLED)
		AddNamedText("check_summary", "Preparation", ChecklistText(), "Manual checklist progress, not automatic inventory detection.", OPTION_FLAG_DISABLED)
		SetCursorPosition(1)
		AddNamedHeader("actions_heading", "Actions")
		AddNamedText("refresh", "Refresh load snapshot", "Read", "With API 1 this updates the existing text and footer without resetting selection.", FeatureFlags())
		AddNamedText("delayed", "Refresh after 2 seconds", "Test", "Teaching example: return control first, then update only if the captured page token remains valid.", DelayedFlags())
		AddNamedText("notify", "Show summary notification", "Show", "The same useful summary can be assigned to an optional keyboard shortcut.", FeatureFlags())
		AddNamedText("go_checklist", "Prepare for the trip", "Open", "Demonstrates SetCurrentPage using an exact raw Pages name.", APIFlags())
		AddNamedText("go_preferences", "Edit trip preferences", "Open", "Sidebar navigation remains available with API extensions off.", APIFlags())
	EndIf
EndEvent

Int Function FeatureFlags()
	If !guideEnabled
		Return OPTION_FLAG_DISABLED
	EndIf
	Return OPTION_FLAG_NONE
EndFunction

Int Function APIFlags()
	If !OpenMCM.IsAPIEnabled()
		Return OPTION_FLAG_DISABLED
	EndIf
	Return OPTION_FLAG_NONE
EndFunction

Int Function DelayedFlags()
	If !guideEnabled || !OpenMCM.IsAPIEnabled()
		Return OPTION_FLAG_DISABLED
	EndIf
	Return OPTION_FLAG_NONE
EndFunction

String Function APIStatus()
	If OpenMCM.IsAPIEnabled()
		Return "Enabled"
	EndIf
	Return "Off — legacy controls available"
EndFunction

; 3. Ordinary numeric callbacks: names resolve only on the CURRENT page.
Event OnOptionSelect(Int a_option)
	Int token = GetPageToken()
	If a_option == GetOptionID("enabled")
		guideEnabled = !guideEnabled
		If !guideEnabled
			CancelPendingRefresh()
		EndIf
		RebindSummaryKey()
		SetToggleOptionValue(a_option, guideEnabled)
		RefreshEnabledGroup(token)
		Return
	EndIf
	If CurrentPage == "Checklist"
		If a_option == GetOptionID("go_overview")
			SetCurrentPage("Overview", token)
		ElseIf guideEnabled
			If a_option == GetOptionID("supplies")
				suppliesReady = !suppliesReady
				SetToggleOptionValue(a_option, suppliesReady)
			ElseIf a_option == GetOptionID("equipment")
				equipmentReady = !equipmentReady
				SetToggleOptionValue(a_option, equipmentReady)
			ElseIf a_option == GetOptionID("route")
				routeReady = !routeReady
				SetToggleOptionValue(a_option, routeReady)
			EndIf
			PaintSummary(token)
		EndIf
	ElseIf CurrentPage == "Preferences"
		If a_option == GetOptionID("go_overview")
			SetCurrentPage("Overview", token)
		EndIf
	Else
		If a_option == GetOptionID("go_checklist")
			SetCurrentPage("Checklist", token)
		ElseIf a_option == GetOptionID("go_preferences")
			SetCurrentPage("Preferences", token)
		ElseIf guideEnabled && a_option == GetOptionID("refresh")
			ReadLoad()
			PaintSummary(token)
		ElseIf guideEnabled && a_option == GetOptionID("delayed")
			QueueRefresh(token)
		ElseIf guideEnabled && a_option == GetOptionID("notify")
			ShowSummary()
		EndIf
	EndIf
EndEvent

Function RefreshEnabledGroup(Int a_token)
	; Flags are also built from guideEnabled above: live presentation is not storage.
	If !IsPageTokenValid(a_token)
		ForcePageReset() ; Synchronous legacy fallback, never used by the worker.
		Return
	EndIf
	String[] keys
	If CurrentPage == "Checklist"
		keys = New String[4]
		keys[0] = "supplies"
		keys[1] = "equipment"
		keys[2] = "route"
		keys[3] = "clear_checks"
	ElseIf CurrentPage != "Preferences"
		keys = New String[3]
		keys[0] = "refresh"
		keys[1] = "notify"
		keys[2] = "delayed"
	Else
		Return ; Preferences stay editable while the guide is disabled.
	EndIf
	SetOptionsEnabled(keys, guideEnabled, a_token)
	SetLiveInfoText("The dependent controls changed together; the page was not rebuilt.", a_token)
EndFunction

Function PaintSummary(Int a_token, Bool a_allowReset = True)
	If !IsPageTokenValid(a_token)
		If a_allowReset
			ForcePageReset() ; Only synchronous callers may use this fallback.
		EndIf
		Return
	EndIf
	If CurrentPage != "Preferences"
		SetOptionText("check_summary", ChecklistText(), a_token)
	EndIf
	If CurrentPage != "Checklist" && CurrentPage != "Preferences"
		SetOptionLabel("load_heading", AccentHeading(), a_token)
		SetOptionText("load", LoadText(), a_token)
		SetOptionText("budget_status", BudgetText(), a_token)
		SetOptionHelp("load", "Latest explicit snapshot. No background polling or inventory changes.", a_token)
	EndIf
	SetLiveInfoText("Snapshot updated. Preferences and checkmarks remain saved with this character.", a_token)
EndFunction

; 4. A delayed job returns from selection first so the manager can unlock.
; This is deliberately a one-shot teaching action, not an automatic poller.
Function QueueRefresh(Int a_token)
	If !guideEnabled || !IsPageTokenValid(a_token)
		Return
	EndIf
	If refreshPending
		SetLiveInfoText("A delayed refresh is already pending.", a_token)
		Return
	EndIf
	CancelPendingRefresh()
	refreshPending = True
	pendingPageToken = a_token
	SendModEvent("OpenMCM_FieldGuide_Refresh", "", refreshGeneration as Float)
EndFunction

Event OnDelayedRefresh(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	Int job = a_numArg as Int
	If a_sender != Self || !refreshPending || job != refreshGeneration
		Return
	EndIf
	Int token = pendingPageToken ; Capture once, before waiting. Never reacquire.
	SetLiveInfoText("Checking in two seconds. Try switching pages to exercise stale-token rejection.", token)
	Utility.WaitMenuMode(2.0)
	If job != refreshGeneration || !refreshPending || !guideEnabled
		Return
	EndIf
	refreshPending = False
	pendingPageToken = 0
	If !IsPageTokenValid(token)
		Return ; Do not reset or touch a different/newly opened page.
	EndIf
	ReadLoad()
	; The snapshot can outlive the UI scope, but its publication must not.
	If IsPageTokenValid(token)
		PaintSummary(token, False)
	EndIf
EndEvent

Function CancelPendingRefresh()
	refreshPending = False
	pendingPageToken = 0
	; Keep the mod-event generation exactly representable by Papyrus Float.
	If refreshGeneration >= 1000000
		refreshGeneration = 0
	EndIf
	refreshGeneration += 1
EndFunction

; 5. Dialogs still use the existing SkyUI typed callbacks/setters.
Event OnOptionSliderOpen(Int a_option)
	If CurrentPage == "Preferences" && a_option == GetOptionID("budget")
		SetSliderDialogStartValue(weightBudget)
		SetSliderDialogDefaultValue(200.0)
		SetSliderDialogRange(25.0, 500.0)
		SetSliderDialogInterval(5.0)
	EndIf
EndEvent

Event OnOptionSliderAccept(Int a_option, Float a_value)
	If CurrentPage == "Preferences" && a_option == GetOptionID("budget") && a_value >= 25.0 && a_value <= 500.0
		weightBudget = a_value
		SetSliderOptionValue(a_option, weightBudget, "{0}")
	EndIf
EndEvent

Event OnOptionMenuOpen(Int a_option)
	If CurrentPage == "Preferences" && a_option == GetOptionID("travel_style")
		SetMenuDialogOptions(styleNames)
		SetMenuDialogStartIndex(travelStyle)
		SetMenuDialogDefaultIndex(0)
	EndIf
EndEvent

Event OnOptionMenuAccept(Int a_option, Int a_index)
	If CurrentPage == "Preferences" && a_option == GetOptionID("travel_style") && a_index >= 0 && a_index < styleNames.Length
		travelStyle = a_index
		SetMenuOptionValue(a_option, styleNames[travelStyle])
	EndIf
EndEvent

Event OnOptionColorOpen(Int a_option)
	If CurrentPage == "Preferences" && a_option == GetOptionID("accent")
		SetColorDialogStartColor(accentColor)
		SetColorDialogDefaultColor(0x80D0FF)
	EndIf
EndEvent

Event OnOptionColorAccept(Int a_option, Int a_color)
	If CurrentPage == "Preferences" && a_option == GetOptionID("accent") && a_color >= 0 && a_color <= 0xFFFFFF
		accentColor = a_color
		SetColorOptionValue(a_option, accentColor)
	EndIf
EndEvent

Event OnOptionInputOpen(Int a_option)
	If CurrentPage == "Preferences" && a_option == GetOptionID("trip_name")
		SetInputDialogStartText(tripName)
	EndIf
EndEvent

Event OnOptionInputAccept(Int a_option, String a_input)
	If CurrentPage == "Preferences" && a_option == GetOptionID("trip_name")
		tripName = StringUtil.Substring(a_input, 0, 40)
		If tripName == ""
			tripName = "Next adventure"
		EndIf
		SetInputOptionValue(a_option, EscapeLabelText(tripName))
	EndIf
EndEvent

Event OnOptionKeyMapChange(Int a_option, Int a_keyCode, String a_conflictControl, String a_conflictName)
	If CurrentPage != "Preferences" || a_option != GetOptionID("summary_key")
		Return
	EndIf
	If a_keyCode >= 0 && (a_keyCode < 1 || a_keyCode > 255)
		ShowMessage("This teaching example accepts keyboard shortcuts only. Use Unmap to leave it disabled.", False)
		Return
	EndIf
	If a_keyCode >= 0 && (a_conflictControl != "" || a_conflictName != "")
		If !ShowMessage("This key is already used by " + a_conflictName + " " + a_conflictControl + ". Assign it anyway?")
			Return
		EndIf
	EndIf
	summaryKey = a_keyCode
	If summaryKey < 0
		summaryKey = -1
	EndIf
	RebindSummaryKey()
	SetKeyMapOptionValue(a_option, summaryKey)
EndEvent

Event OnOptionDefault(Int a_option)
	If a_option == GetOptionID("enabled")
		guideEnabled = True
		RebindSummaryKey()
		SetToggleOptionValue(a_option, True)
		RefreshEnabledGroup(GetPageToken())
	ElseIf CurrentPage == "Preferences"
		If a_option == GetOptionID("budget")
			weightBudget = 200.0
			SetSliderOptionValue(a_option, weightBudget, "{0}")
		ElseIf a_option == GetOptionID("travel_style")
			travelStyle = 0
			SetMenuOptionValue(a_option, styleNames[0])
		ElseIf a_option == GetOptionID("accent")
			accentColor = 0x80D0FF
			SetColorOptionValue(a_option, accentColor)
		ElseIf a_option == GetOptionID("trip_name")
			tripName = "Next adventure"
			SetInputOptionValue(a_option, tripName)
		ElseIf a_option == GetOptionID("summary_key")
			summaryKey = -1
			RebindSummaryKey()
			SetKeyMapOptionValue(a_option, summaryKey)
		EndIf
	ElseIf CurrentPage == "Checklist" && guideEnabled
		If a_option == GetOptionID("supplies")
			suppliesReady = False
			SetToggleOptionValue(a_option, False)
		ElseIf a_option == GetOptionID("equipment")
			equipmentReady = False
			SetToggleOptionValue(a_option, False)
		ElseIf a_option == GetOptionID("route")
			routeReady = False
			SetToggleOptionValue(a_option, False)
		EndIf
		PaintSummary(GetPageToken())
	EndIf
EndEvent

Event OnOptionHighlight(Int a_option)
	; Automatic named help handles the enabled API path. Demonstrate an explicit
	; legacy fallback instead of silently losing help when the player opts out.
	If !OpenMCM.IsAPIEnabled()
		SetInfoText("Field Guide stores a manual checklist and trip preferences in this save. Normal controls and sidebar pages work. Enable API 1 in OpenMCM > Status > Runtime for live updates and navigation buttons.")
	EndIf
EndEvent

State ResetChecklist
	Event OnSelectST()
		If guideEnabled && ShowMessage("Clear supplies, equipment and route checkmarks? Trip preferences will be kept.")
			ClearChecklist()
		EndIf
	EndEvent

	Event OnDefaultST()
		ClearChecklist()
	EndEvent

	Event OnHighlightST()
		If !OpenMCM.IsAPIEnabled()
			SetInfoText("Clear the three checkmarks, keeping your trip name, style, budget, colour and hotkey.")
		EndIf
	EndEvent
EndState

Function ClearChecklist()
	If !guideEnabled || CurrentPage != "Checklist"
		Return
	EndIf
	suppliesReady = False
	equipmentReady = False
	routeReady = False
	SetToggleOptionValue(GetOptionID("supplies"), False)
	SetToggleOptionValue(GetOptionID("equipment"), False)
	SetToggleOptionValue(GetOptionID("route"), False)
	PaintSummary(GetPageToken())
EndFunction

; 6. Read-only gameplay integration. No actor/inventory/quest writes or polling.
Function ReadLoad()
	Actor player = Game.GetPlayer()
	playerAvailable = player != None
	If !playerAvailable
		carriedWeight = 0.0
		carryCapacity = 0.0
		Return
	EndIf
	carriedWeight = player.GetActorValue("InventoryWeight")
	carryCapacity = player.GetActorValue("CarryWeight")
EndFunction

String Function LoadText()
	If !playerAvailable
		Return "Player not available"
	EndIf
	Return (carriedWeight as Int) + " / " + (carryCapacity as Int)
EndFunction

String Function BudgetText()
	If !playerAvailable
		Return "Target: " + (weightBudget as Int)
	EndIf
	If carriedWeight > weightBudget
		Return ((carriedWeight - weightBudget) as Int) + " over target " + (weightBudget as Int)
	EndIf
	Return ((weightBudget - carriedWeight) as Int) + " left of target " + (weightBudget as Int)
EndFunction

String Function ChecklistText()
	Int ready = (suppliesReady as Int) + (equipmentReady as Int) + (routeReady as Int)
	Return ready + " / 3 ready"
EndFunction

String Function AccentHeading()
	String digits = "0123456789ABCDEF"
	String hex = ""
	Int color = accentColor
	Int i = 0
	While i < 6
		hex = StringUtil.Substring(digits, color % 16, 1) + hex
		color = color / 16
		i += 1
	EndWhile
	Return "<font color='#" + hex + "'>Load snapshot</font>"
EndFunction

; Store user input as plain text. Escape it only for HTML-capable MCM fields;
; keep the input dialog's editable text and notifications unescaped.
String Function EscapeLabelText(String a_text)
	String result = ""
	Int i = 0
	While i < StringUtil.GetLength(a_text)
		String ch = StringUtil.Substring(a_text, i, 1)
		If ch == "&"
			result += "&amp;"
		ElseIf ch == "<"
			result += "&lt;"
		ElseIf ch == ">"
			result += "&gt;"
		Else
			result += ch
		EndIf
		i += 1
	EndWhile
	Return result
EndFunction

Function RebindSummaryKey()
	UnregisterForAllKeys() ; Only this script's registrations, not other mods'.
	If guideEnabled && summaryKey >= 1 && summaryKey <= 255
		RegisterForKey(summaryKey)
	EndIf
EndFunction

String Function GetCustomControl(Int a_keyCode)
	If guideEnabled && summaryKey >= 1 && a_keyCode == summaryKey
		Return "Field Guide summary"
	EndIf
	Return ""
EndFunction

Event OnKeyDown(Int keyCode)
	If guideEnabled && summaryKey >= 1 && keyCode == summaryKey && !Utility.IsInMenuMode()
		ShowSummary()
	EndIf
EndEvent

Function ShowSummary()
	If !guideEnabled
		Return
	EndIf
	ReadLoad()
	Debug.Notification(tripName + ": " + ChecklistText() + " | Load " + LoadText() + " | Target " + (weightBudget as Int))
EndFunction
