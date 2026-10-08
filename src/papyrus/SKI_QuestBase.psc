Scriptname SKI_QuestBase extends Quest Hidden

; Public SkyUI-compatible quest lifecycle contract.
Int Property CurrentVersion Auto Hidden

Function CheckVersion()
	Int targetVersion = GetVersion()
	If CurrentVersion < targetVersion
		OnVersionUpdateBase(targetVersion)
		OnVersionUpdate(targetVersion)
		CurrentVersion = targetVersion
	EndIf
EndFunction

Int Function GetVersion()
	Return 1
EndFunction

Event OnVersionUpdateBase(Int a_version)
EndEvent

Event OnVersionUpdate(Int a_version)
EndEvent

Event OnGameReload()
EndEvent
