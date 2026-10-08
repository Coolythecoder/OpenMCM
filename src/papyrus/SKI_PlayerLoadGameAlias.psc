Scriptname SKI_PlayerLoadGameAlias extends ReferenceAlias

Event OnPlayerLoadGame()
	SKI_QuestBase owner = GetOwningQuest() as SKI_QuestBase
	If owner != None
		owner.OnGameReload()
	EndIf
EndEvent
