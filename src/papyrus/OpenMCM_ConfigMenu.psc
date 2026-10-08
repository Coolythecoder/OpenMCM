Scriptname OpenMCM_ConfigMenu extends SKI_ConfigBase

; A small built-in provider gives every installation one known-good MCM. This
; mirrors SkyUI's own built-in config quest and makes manager/bridge failures
; distinguishable from a third-party provider that never instantiated.

; Rows are rebuilt on every open; no provider save migration is required.
Int Function GetVersion()
	Return 1
EndFunction

Event OnConfigManagerReady(String a_eventName, String a_strArg, Float a_numArg, Form a_sender)
	; 0x820 was SkyUI's own persistent configuration quest. OpenMCM 0.2.7
	; temporarily reused it, so an upgraded save can retain that older script
	; instance. Coexistence uses its own plugin and must never register the
	; old standalone provider as well. A present but malformed companion fails
	; closed instead of falling back to a stale instance from another mode.
	If Game.GetModByName("OpenMCM.esp") != 255
		If Game.GetFormFromFile(0x000800, "OpenMCM.esp") != Self
			Return
		EndIf
	ElseIf Game.GetFormFromFile(0x000830, "SkyUI_SE.esp") != Self
		Return
	EndIf
	Parent.OnConfigManagerReady(a_eventName, a_strArg, a_numArg, a_sender)
EndEvent

Event OnConfigInit()
	ModName = "OpenMCM"
	Pages = New String[1]
	Pages[0] = "Status"
EndEvent

Event OnPageReset(String a_page)
	SetTitleText("OpenMCM")
	SetCursorFillMode(TOP_TO_BOTTOM)
	AddHeaderOption("Runtime")
	AddTextOption("MCM host", "Online")
	AddTextOption("SkyUI MCM API", "Version 4")
	AddTextOption("OpenMCM API", "Version " + OpenMCM.GetAPIVersion())
	AddToggleOptionST("ExtendedAPI", "Enable OpenMCM API", OpenMCM.IsAPIEnabled())
	AddHeaderOption("Compatibility")
	AddTextOption("Classic MCM menus", "Supported")
	AddTextOption("MCM Helper menus", "Supported")
	AddHeaderOption("Troubleshooting")
	AddToggleOptionST("MouseDiagnostics", "Mouse input diagnostics", UI.GetBool("Journal Menu", "_root.ConfigPanelFader.configPanel.mouseDiagnosticsEnabled"))
EndEvent

Function SetExtendedAPIEnabled(Bool a_enabled)
	SKI_ConfigManager manager = Game.GetFormFromFile(0x000802, "SkyUI_SE.esp") as SKI_ConfigManager
	If manager != None
		manager.SetOpenMCMAPIEnabled(a_enabled)
	EndIf
	; A changed preference invalidates outstanding optional work. Rebuild the
	; status page so it receives a fresh scope and displays the saved choice.
	ForcePageReset()
EndFunction

State ExtendedAPI
	Event OnSelectST()
		SetExtendedAPIEnabled(!OpenMCM.IsAPIEnabled())
	EndEvent

	Event OnDefaultST()
		SetExtendedAPIEnabled(False)
	EndEvent

	Event OnHighlightST()
		SetInfoText("Enables API 1 automatic help and live text updates, page navigation and conditional option groups in mods written for OpenMCM. Off by default; saved with this savegame. SkyUI API 4, MCM Helper and normal controls stay available. No native DLL required. This does not upgrade existing MCMs or fix exit crashes.")
	EndEvent
EndState

State MouseDiagnostics
	Event OnSelectST()
		Bool enabled = !UI.GetBool("Journal Menu", "_root.ConfigPanelFader.configPanel.mouseDiagnosticsEnabled")
		UI.InvokeBool("Journal Menu", "_root.ConfigPanelFader.configPanel.setMouseDiagnostics", enabled)
		SetToggleOptionValueST(enabled)
	EndEvent

	Event OnHighlightST()
		SetInfoText("Shows mouse delivery, pointer position and the picked Flash target. Use the keyboard to enable it, return to the mod list, then move and click a mod name. This collects evidence; it does not change input routing.")
	EndEvent
EndState
