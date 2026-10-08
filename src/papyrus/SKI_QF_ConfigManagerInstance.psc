; Compatibility quest fragment for the traditional `setstage SKI_ConfigManagerInstance 1` repair path.
Scriptname SKI_QF_ConfigManagerInstance extends Quest Hidden

ReferenceAlias Property Alias_PlayerRef Auto

Function Fragment_0()
	Quest ownerQuest = Self as Quest
	SKI_ConfigManager manager = ownerQuest as SKI_ConfigManager
	If manager != None
		manager.ForceReset()
	EndIf
EndFunction
