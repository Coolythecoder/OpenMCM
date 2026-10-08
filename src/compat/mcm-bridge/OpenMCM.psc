Scriptname OpenMCM Hidden

; Basic MCM Bridge adapter, not the OpenMCM Journal host.
; Original OpenMCM code: GPL-3.0-or-later; see the accompanying LICENSE.txt.
; SDK signatures remain API 1. Only named option construction is supported.
Int Function GetAPIVersion() Global
	Return 1
EndFunction

Bool Function IsAPIEnabled() Global
	; There is no OpenMCM Runtime switch or extended host in this installation.
	Return False
EndFunction

Int Function GetHostAPIVersion() Global
	Return 0
EndFunction

Bool Function HasCapability(String a_capability) Global
	Return a_capability == "named_options"
EndFunction
