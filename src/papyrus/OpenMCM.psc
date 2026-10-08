Scriptname OpenMCM Hidden

; SDK version, independent of SkyUI's MCM API 4 and a provider's GetVersion().
Int Function GetAPIVersion() Global
	Return 1
EndFunction

; Save-local user preference, also readable while the Journal is closed.
; Both installation modes retain the original SkyUI manager form identity.
Bool Function IsAPIEnabled() Global
	SKI_ConfigManager manager = Game.GetFormFromFile(0x000802, "SkyUI_SE.esp") as SKI_ConfigManager
	Return manager != None && manager.IsOpenMCMAPIEnabled()
EndFunction

; Returns zero when the Journal movie/API is unavailable OR disabled. This
; is not a test for an installed plugin while the menu is closed.
Int Function GetHostAPIVersion() Global
	Return UI.GetInt("Journal Menu", "_root.ConfigPanelFader.configPanel.openMCMApiVersion")
EndFunction

; Capabilities of this installed SDK, independent of the user's enable choice.
; Optional live operations additionally validate enable state, active host and
; page token. Named control construction still works with extensions disabled.
; Unknown names always return false.
Bool Function HasCapability(String a_capability) Global
	Return a_capability == "named_options" || a_capability == "automatic_help" || a_capability == "live_text" || a_capability == "page_tokens" || a_capability == "page_navigation" || a_capability == "conditional_groups"
EndFunction
