Scriptname Form Hidden

Int Function GetFormID() Native
Function RegisterForSingleUpdate(Float afInterval) Native
Function RegisterForMenu(String asMenuName) Native
Function RegisterForModEvent(String asEventName, String asCallbackName) Native
Function UnregisterForModEvent(String asEventName) Native
Function SendModEvent(String asEventName, String asStrArg = "", Float afNumArg = 0.0) Native
Function RegisterForKey(Int keyCode) Native
Function UnregisterForAllKeys() Native

Event OnKeyDown(Int keyCode)
EndEvent
